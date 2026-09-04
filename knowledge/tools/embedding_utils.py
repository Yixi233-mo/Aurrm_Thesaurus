# knowledge/tools/embedding_utils.py

import os
import sys
import logging
import threading
from typing import Optional, List, Dict, Any, Union

# 兼容 torch 2.4.x 的安全限制（CVE-2025-32434）：
# torch >= 2.6 不再需要此环境变量
os.environ.setdefault('TORCH_FORCE_WEIGHTS_ONLY_FAIL', '1')

from knowledge.core import env  # noqa: F401 - 加载项目根目录 .env

# 修复依赖冲突：
# 1. 用户全局目录的 pyarrow DLL 损坏 → 预导入 conda 环境的 pyarrow
# 2. 用户全局目录的 FlagEmbedding 不完整 → 使用项目 libs 目录中的干净安装
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LIBS_DIR = os.path.join(_PROJECT_ROOT, "libs")
_user_site = os.path.join(os.environ.get("APPDATA", ""), "Python", "Python310", "site-packages")
_has_user_site = any("Roaming" in p and "site-packages" in p for p in sys.path)

if _has_user_site:
    # 1. 临时移除用户目录
    _saved_path = list(sys.path)
    sys.path = [p for p in sys.path if not ("Roaming" in p and "site-packages" in p)]
    # 2. 从 conda 环境预导入 pyarrow（缓存到 sys.modules）
    try:
        import pyarrow
        import pyarrow.lib
    except ImportError:
        pass
    # 3. 加回项目 libs 目录（干净的 FlagEmbedding）
    if os.path.isdir(_LIBS_DIR):
        sys.path.insert(0, _LIBS_DIR)

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

# 从归一化模块导入（在同一目录下）
from knowledge.tools.normalize_sparse_vector import normalize_sparse_vector

logger = logging.getLogger(__name__)

# ================================================================== #
#                     BGE-M3 嵌入模型（稠密 + 稀疏）                   #
# ================================================================== #

_bge_m3_model = None   # transformers 模型实例
_bge_m3_tokenizer = None
_bge_m3_device = "cpu"
_bge_m3_use_fp16 = False
_bge_m3_lock = threading.Lock()


class _BGE3EmbeddingFunction:
    """BGE-M3 嵌入函数（绕过 pymilvus BGEM3EmbeddingFunction 的 meta tensor bug）。

    提供与 pymilvus BGEM3EmbeddingFunction 兼容的接口：
      - encode_documents(docs) -> {"dense": [...], "sparse": csr_matrix}
      - encode_queries(queries) -> {"dense": [...], "sparse": csr_matrix}

    使用 transformers 直接加载模型 + 独立加载 colbert_linear / sparse_linear，
    支持 CUDA 推理。
    """

    # BGE-M3 词汇表大小（含特殊 token）
    _VOCAB_SIZE = 250002

    def __init__(self, model_path: str, device: str = "cpu", use_fp16: bool = False):
        import torch
        import numpy as np
        from transformers import AutoTokenizer, AutoModel
        from scipy.sparse import csr_matrix

        self._torch = torch
        self._np = np
        self._csr_matrix = csr_matrix

        logger.info(f"加载 BGE-M3: path={model_path}, device={device}, fp16={use_fp16}")

        # 1. 加载基础模型（XLM-RoBERTa）
        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._model = AutoModel.from_pretrained(model_path)

        # 2. 加载 BGE-M3 专用层（colbert_linear + sparse_linear）
        colbert_state = torch.load(
            os.path.join(model_path, "colbert_linear.pt"),
            map_location="cpu", weights_only=False,
        )
        sparse_state = torch.load(
            os.path.join(model_path, "sparse_linear.pt"),
            map_location="cpu", weights_only=False,
        )

        # colbert_linear: Linear(1024, 1024), 用于稠密向量变换
        self._colbert_linear = torch.nn.Linear(1024, 1024)
        self._colbert_linear.load_state_dict(colbert_state, assign=True)

        # sparse_linear: Linear(1024, 1), 用于 token 级重要性打分
        self._sparse_linear = torch.nn.Linear(1024, 1)
        self._sparse_linear.load_state_dict(sparse_state, assign=True)

        # 3. 移动到目标设备
        self._device = device
        cuda_available = torch.cuda.is_available()
        target_device = torch.device(device) if (device.startswith("cuda") and cuda_available) else torch.device("cpu")

        self._model = self._model.to(target_device).eval()
        self._colbert_linear = self._colbert_linear.to(target_device).eval()
        self._sparse_linear = self._sparse_linear.to(target_device).eval()

        if use_fp16 and target_device.type == "cuda":
            self._model = self._model.half()
            self._colbert_linear = self._colbert_linear.half()
            self._sparse_linear = self._sparse_linear.half()

        # 同步 dtype：确保线性层与模型主权重一致
        model_dtype = next(self._model.parameters()).dtype
        self._colbert_linear = self._colbert_linear.to(model_dtype)
        self._sparse_linear = self._sparse_linear.to(model_dtype)

        logger.info(f"BGE-M3 加载成功，设备: {target_device}")

    def encode_documents(self, documents: list) -> dict:
        """编码文档，返回稠密 + 稀疏向量。"""
        return self._encode(documents)

    def encode_queries(self, queries: list) -> dict:
        """编码查询，返回稠密 + 稀疏向量。"""
        return self._encode(queries)

    def _encode(self, texts: list) -> dict:
        torch = self._torch
        np = self._np
        csr_matrix = self._csr_matrix

        if not texts:
            return {"dense": np.array([]), "sparse": csr_matrix((0, 0))}

        # 1. Tokenize
        inputs = self._tokenizer(
            texts, return_tensors="pt", padding=True,
            truncation=True, max_length=512,
        )

        # 2. 移动到设备
        device = next(self._model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # 3. 全部推理在 no_grad 中执行
        with torch.no_grad():
            outputs = self._model(**inputs)
            token_embeddings = outputs.last_hidden_state  # (B, L, 1024)

            # 稠密向量：CLS token → colbert_linear → L2 normalize
            cls_embeddings = token_embeddings[:, 0]  # (B, 1024)
            dense_vectors = self._colbert_linear(cls_embeddings)  # (B, 1024)
            dense_vectors = torch.nn.functional.normalize(dense_vectors, p=2, dim=-1)

            # 稀疏向量：token 级重要性打分
            token_scores = self._sparse_linear(token_embeddings).squeeze(-1)  # (B, L)
            token_scores = torch.nn.functional.relu(token_scores)

        dense_list = dense_vectors.cpu().numpy()  # (B, 1024)
        token_scores_np = token_scores.cpu().numpy()
        attention_mask = inputs['attention_mask'].cpu().numpy()
        input_ids_np = inputs['input_ids'].cpu().numpy()

        # 6. 构建稀疏 CSR 矩阵
        sparse_indices_list = []
        sparse_values_list = []
        col_ptr = [0]

        for i in range(len(texts)):
            mask = attention_mask[i].astype(bool)
            ids = input_ids_np[i][mask]
            sc = token_scores_np[i][mask]

            # 过滤低权重 token（保留有意义的 token）
            nonzero_mask = sc > 0.001
            ids = ids[nonzero_mask] + 1  # +1 偏移，避免与 padding(0) 冲突
            sc = sc[nonzero_mask]

            sparse_indices_list.append(ids.astype(np.int32))
            sparse_values_list.append(sc.astype(np.float32))
            col_ptr.append(col_ptr[-1] + len(ids))

        total_nnz = col_ptr[-1]
        if total_nnz > 0:
            all_indices = np.concatenate(sparse_indices_list)
            all_values = np.concatenate(sparse_values_list)
            sparse_matrix = csr_matrix(
                (all_values, all_indices, np.array(col_ptr)),
                shape=(len(texts), self._VOCAB_SIZE),
            )
        else:
            sparse_matrix = csr_matrix((len(texts), self._VOCAB_SIZE))

        return {"dense": dense_list, "sparse": sparse_matrix}


def get_bge_m3_model():
    """获取 BGE-M3 嵌入模型单例（使用 transformers 直接加载，绕过 pymilvus meta tensor bug）。"""
    global _bge_m3_model

    if _bge_m3_model is not None:
        return _bge_m3_model

    with _bge_m3_lock:
        # 双重检查：可能在锁等待期间已被其他线程初始化
        if _bge_m3_model is not None:
            return _bge_m3_model

        model_path = os.getenv('BGE_M3_PATH', 'BAAI/bge-m3')
        device = os.getenv('BGE_DEVICE', 'cpu')
        use_fp16_str = os.getenv('BGE_FP16', 'False')
        use_fp16 = use_fp16_str.lower() in ('true', '1', 'yes')

        try:
            _bge_m3_model = _BGE3EmbeddingFunction(
                model_path=model_path,
                device=device,
                use_fp16=use_fp16,
            )
        except Exception as e:
            logger.error(f"BGE-M3 加载失败: {e}")
            _bge_m3_model = None

        return _bge_m3_model


# 兼容旧拼写错误（保留）
def get_beg_m3_embedding_model():
    return get_bge_m3_model()


def generate_hybrid_embeddings(
    embedding_model,
    embedding_documents: List[str],
    normalize_sparse: bool = True,
) -> Optional[Dict[str, List[Any]]]:
    """
    为文本列表生成混合嵌入（稠密 + 稀疏向量）。

    Args:
        embedding_model: BGE-M3 模型实例
        embedding_documents: 待嵌入的文本列表
        normalize_sparse: 是否对稀疏向量 L2 归一化（默认开启）

    Returns:
        {
            "dense": List[List[float]]，每个文本的稠密向量（1024维）,
            "sparse": List[Dict[int, float]]，每个文本的稀疏向量
        }
        失败返回 None
    """
    if not embedding_documents:
        return {"dense": [], "sparse": []}

    try:
        result = embedding_model.encode_documents(embedding_documents)

        # 稠密向量
        dense_vectors = [vec.tolist() for vec in result["dense"]]

        # 稀疏向量（CSR → Dict）
        csr = result["sparse"]
        sparse_vectors = []
        for i in range(len(embedding_documents)):
            start = csr.indptr[i]
            end = csr.indptr[i + 1]
            token_ids = csr.indices[start:end].tolist()
            weights = csr.data[start:end].tolist()
            sparse_dict = dict(zip(token_ids, weights))

            if normalize_sparse:
                sparse_dict = normalize_sparse_vector(sparse_dict)

            sparse_vectors.append(sparse_dict)

        logger.debug(f"混合嵌入生成成功，文档数: {len(embedding_documents)}")
        return {"dense": dense_vectors, "sparse": sparse_vectors}

    except Exception as e:
        logger.error(f"混合嵌入生成失败: {e}")
        return None


# ================================================================== #
#                  OpenAI 嵌入模型（仅稠密，1536维）                   #
# ================================================================== #

_openai_embeddings: Optional[OpenAIEmbeddings] = None


def get_openai_embeddings_client() -> Optional[OpenAIEmbeddings]:
    """
    获取 OpenAI Embeddings 客户端单例（用于 text-embedding-v4 等）。

    环境变量：
        OPENAI_API_KEY: API 密钥
        OPENAI_API_BASE: API 基础 URL（可指向阿里云 DashScope 等兼容端点）
        OPENAI_EMBEDDING_MODEL: 模型名称，默认 "text-embedding-v4"

    Returns:
        OpenAIEmbeddings 实例，失败返回 None
    """
    global _openai_embeddings

    if _openai_embeddings is not None:
        return _openai_embeddings

    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-v4")

    if not api_key:
        logger.warning("OPENAI_API_KEY 未配置，无法创建 OpenAI Embeddings 客户端")
        return None

    try:
        _openai_embeddings = OpenAIEmbeddings(
            model=model,
            openai_api_key=api_key,
            openai_api_base=api_base,
        )
        logger.info(f"OpenAI Embeddings 客户端创建成功: model={model}")
    except Exception as e:
        logger.error(f"OpenAI Embeddings 客户端创建失败: {e}")
        _openai_embeddings = None

    return _openai_embeddings


def embed_text_to_dense_vector(
    text: str,
    client: Optional[OpenAIEmbeddings] = None,
) -> Optional[List[float]]:
    """
    使用 OpenAI Embeddings 将单个文本转为稠密向量。

    Args:
        text: 待嵌入的文本
        client: OpenAIEmbeddings 实例，若为 None 则自动获取

    Returns:
        稠密向量列表（1536维），失败返回 None
    """
    if not text:
        return None

    if client is None:
        client = get_openai_embeddings_client()
        if client is None:
            return None

    try:
        vectors = client.embed_documents([text])
        if vectors and len(vectors) > 0:
            return vectors[0]
        return None
    except Exception as e:
        logger.error(f"OpenAI 文本嵌入失败: {e}")
        return None


def embed_texts_to_dense_vectors(
    texts: List[str],
    client: Optional[OpenAIEmbeddings] = None,
) -> Optional[List[List[float]]]:
    """
    批量文本转为稠密向量。

    Args:
        texts: 文本列表
        client: OpenAIEmbeddings 实例，若为 None 则自动获取

    Returns:
        稠密向量列表，失败返回 None
    """
    if not texts:
        return []

    if client is None:
        client = get_openai_embeddings_client()
        if client is None:
            return None

    try:
        return client.embed_documents(texts)
    except Exception as e:
        logger.error(f"OpenAI 批量文本嵌入失败: {e}")
        return None


# ================================================================== #
#              显式导出 normalize_sparse_vector（供外部使用）          #
# ================================================================== #

# 直接从 normalize_sparse_vector 模块导出，确保 from embedding_utils import normalize_sparse_vector 可用
# 已在文件顶部导入，此处仅作明确标记

__all__ = [
    "get_bge_m3_model",
    "get_beg_m3_embedding_model",  # 兼容旧名
    "generate_hybrid_embeddings",
    "get_openai_embeddings_client",
    "embed_text_to_dense_vector",
    "embed_texts_to_dense_vectors",
    "normalize_sparse_vector",
]

# ================================================================== #
#                           测试入口                                   #
# ================================================================== #

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("测试 embedding_utils 模块")
    print("=" * 60)

    # 测试 BGE-M3
    print("\n--- 1. BGE-M3 模型加载 ---")
    bge_model = get_bge_m3_model()
    if bge_model:
        print("✓ BGE-M3 加载成功")

        print("\n--- 2. 混合嵌入生成 ---")
        docs = ["我是中国人", "我喜欢自由"]
        result = generate_hybrid_embeddings(bge_model, docs)
        if result:
            print(f"  稠密向量维度: {len(result['dense'][0])}")
            print(f"  稀疏向量非零项数: {len(result['sparse'][0])}")

    # 测试 OpenAI
    print("\n--- 3. OpenAI Embeddings 客户端 ---")
    openai_client = get_openai_embeddings_client()
    if openai_client:
        print("✓ OpenAI 客户端创建成功")
        vec = embed_text_to_dense_vector("测试文本", openai_client)
        if vec:
            print(f"  OpenAI 稠密向量维度: {len(vec)}")
    else:
        print("⚠ OpenAI 客户端未配置（跳过）")

    # 测试 normalize_sparse_vector 导出
    print("\n--- 4. 验证 normalize_sparse_vector 导出 ---")
    try:
        from knowledge.tools.embedding_utils import normalize_sparse_vector as ns
        print(f"✓ normalize_sparse_vector 可导入，函数名: {ns.__name__}")
    except ImportError as e:
        print(f"✗ 导入失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)