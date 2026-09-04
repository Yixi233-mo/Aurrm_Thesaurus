"""
BGE-M3 向量化节点

为文档切片生成稠密和稀疏向量
"""
import json
import os
from typing import List

from knowledge.processor.import_process.base import BaseNode, setup_logging
from knowledge.processor.import_process.state import ImportGraphState
from knowledge.processor.import_process.config import get_config
from knowledge.processor.import_process.exceptions import EmbeddingError
from knowledge.tools.embedding_utils import get_bge_m3_model
from knowledge.tools.normalize_sparse_vector import normalize_sparse_vector


class BgeEmbeddingNode(BaseNode):
    """
    BGE-M3 向量化节点

    为每个切片生成稠密向量和稀疏向量，
    用于后续的向量检索。
    """

    name = "bge_embedding"

    def process(self, state: ImportGraphState) -> ImportGraphState:
        """
        执行向量化

        Args:
            state: 图状态

        Returns:
            更新后的状态（chunks 中包含向量）
        """
        config = get_config()

        # 获取切片
        chunks = state.get("chunks", [])
        if not isinstance(chunks, list) or not chunks:
            raise EmbeddingError("chunks 为空或无效", node_name=self.name)

        self.log_step("step_1", f"开始为 {len(chunks)} 个切片生成向量")

        # 初始化 BGE-M3
        try:
            bge_m3_ef = get_bge_m3_model()
        except Exception as e:
            raise EmbeddingError(f"初始化 BGE-M3 失败: {e}", node_name=self.name, cause=e)

        if bge_m3_ef is None:
            raise EmbeddingError(
                "BGE-M3 模型加载失败（返回 None），请检查模型路径和环境变量 BGE_M3_PATH",
                node_name=self.name
            )

        # 批量处理
        output_data = []
        batch_size = config.embedding_batch_size

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_output = self._process_batch(bge_m3_ef, batch, i, len(chunks))
            output_data.extend(batch_output)

        self.log_step("step_2", f"向量化完成，共 {len(output_data)} 个切片")
        state["chunks"] = output_data

        return state

    def _process_batch(
            self,
            bge_m3_ef,
            batch: List[dict],
            start_idx: int,
            total: int
    ) -> List[dict]:
        """处理一个批次的切片"""
        try:
            # 构造输入文本：item_name + content
            texts = [
                (doc.get("item_name", "") or "") + "\n" + (doc.get("content", "") or "")
                for doc in batch
            ]

            # 批量生成向量
            embeddings = bge_m3_ef.encode_documents(texts)

            if not embeddings:
                self.logger.warning(f"批次 {start_idx + 1}-{start_idx + len(batch)} 未能生成向量")
                return batch

            # 处理结果
            output = []
            for j, doc in enumerate(batch):
                # 提取稠密向量
                dense_vector = embeddings["dense"][j].tolist()

                # 提取稀疏向量
                start = embeddings["sparse"].indptr[j]
                end = embeddings["sparse"].indptr[j + 1]
                token_ids = embeddings["sparse"].indices[start:end].tolist()
                weights = embeddings["sparse"].data[start:end].tolist()
                sparse_dict = dict(zip(token_ids, weights))
                sparse_vector = normalize_sparse_vector(sparse_dict)

                # 构建输出
                item = {
                    "content": doc.get("content"),
                    "title": doc.get("title"),
                    "parent_title": doc.get("parent_title", ""),
                    "part": doc.get("part", 0),
                    "file_title": doc.get("file_title"),
                    "item_name": doc.get("item_name"),
                    "dense_vector": dense_vector,
                    "sparse_vector": sparse_vector
                }
                output.append(item)

            self.logger.info(
                f"成功处理批次 {start_idx + 1}-{min(start_idx + len(batch), total)}/{total}"
            )
            return output

        except Exception as e:
            raise EmbeddingError(
                f"批次 {start_idx + 1}-{start_idx + len(batch)} 处理失败: {e}",
                node_name="bge_embedding",
                cause=e
            )