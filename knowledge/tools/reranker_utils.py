"""Reranker 模型加载工具

优先使用 pip 安装的 FlagEmbedding，仅在失败时回退到项目 libs/ 目录。
这样即使 libs/ 目录不存在（gitignore），新环境也能正常加载模型。
"""
import os
import sys
import logging

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logger = logging.getLogger(__name__)
_reranker_model = None


def _load_flag_embedding():
    """加载 FlagEmbedding，优先 pip 安装，回退 libs/ 目录。"""
    # 1. 优先使用 pip 安装的 FlagEmbedding（正常环境）
    try:
        from FlagEmbedding import FlagReranker
        return FlagReranker
    except ImportError:
        logger.debug("pip FlagEmbedding 不可用，尝试 libs/ 回退")

    # 2. 回退到项目 libs/ 目录
    _LIBS_DIR = os.path.join(_PROJECT_ROOT, "libs")
    if not os.path.isdir(_LIBS_DIR):
        raise ImportError(
            "FlagEmbedding 未安装且 libs/ 目录不存在。"
            "请运行: pip install FlagEmbedding"
        )

    # 清理用户 site-packages 中可能不完整的旧安装
    _user_site = os.path.join(os.environ.get("APPDATA", ""), "Python", "Python310", "site-packages")
    _has_user_site = any("Roaming" in p and "site-packages" in p for p in sys.path)

    if _has_user_site:
        _saved_path = list(sys.path)
        sys.path = [p for p in sys.path if not ("Roaming" in p and "site-packages" in p)]
        try:
            import pyarrow
            import pyarrow.lib
        except ImportError:
            pass
        sys.path.insert(0, _LIBS_DIR)
    else:
        sys.path.insert(0, _LIBS_DIR)

    try:
        from FlagEmbedding import FlagReranker
        return FlagReranker
    except ImportError:
        # 恢复 sys.path
        if _has_user_site:
            sys.path = _saved_path
        raise


def get_reranker_model():
    """
    获取 Reranker 模型实例（单例模式）
    """
    global _reranker_model
    try:
        if _reranker_model is None:
            FlagReranker = _load_flag_embedding()
            model_path = os.getenv("BGE_RERANKER_LARGE")
            device = os.getenv("BGE_RERANKER_DEVICE", "cpu")
            use_fp16 = os.getenv("BGE_RERANKER_FP16", "False").lower() == "true"

            logger.info(f"正在初始化 Reranker 模型，路径: {model_path}, 设备: {device}, fp16: {use_fp16}")

            _reranker_model = FlagReranker(
                model_name_or_path=model_path,
                device=device,
                use_fp16=use_fp16
            )

            logger.info("Reranker 模型初始化成功！")

        return _reranker_model

    except Exception as e:
        logger.error(f"初始化 Reranker 模型失败: {e}", exc_info=True)
        return None


if __name__ == '__main__':
    reranker = get_reranker_model()

    # [0.1,0.2,0.3]=reranker.compute_score()
    # print(reranker)

    query = "1956年发生了哪一事件标志着人工智能这一学科的正式诞生？"

    documents = [
        "1950 年，艾伦·图灵发表了其具有里程碑意义的论文《计算机与智能》，将图灵测试作为衡量智能的标准，这一概念在人工智能的哲学研究和发展中具有基础性意义。",
        "1956 年的达特茅斯会议被认为是人工智能作为一个学科领域的诞生之地；在此会议上，约翰·麦卡锡等人创造了“人工智能”这一术语，并明确了其基本目标.",
        "1951 年，英国数学家兼计算机科学家艾伦·图灵也开发出了首个用于下棋的程序，这展示了人工智能在游戏策略方面的一个早期应用实例.",
        "1955 年，艾伦·纽厄尔、赫伯特·A·西蒙和克利夫·肖共同发明的“逻辑理论家”程序标志着首个真正的人工智能程序的诞生，该程序能够解决逻辑问题，类似于证明数学定理。."
    ]
    pairs = [(query, doc) for doc in documents]
    scores = reranker.compute_score(pairs)

    print(scores)
