"""向量搜索节点

对用户查询进行向量化，在 Milvus 中执行混合搜索（稠密 + 稀疏），返回相关切片。
"""

import os
from typing import List

from knowledge.processor.query_process.base import BaseNode, setup_logging, build_filter_expr
from knowledge.processor.query_process.state import QueryGraphState


class SearchEmbeddingNode(BaseNode):
    """向量搜索节点。

    流程: 查询向量化 → 构建混合搜索请求 → 执行检索 → 返回结果
    """

    name = "search_embedding"

    SEARCH_TOP_K = 10
    RERANK_TOP_K = 5
    RANKER_WEIGHTS = (0.5, 0.5)
    OUTPUT_FIELDS = ["chunk_id", "content", "item_name", "title"]

    def process(self, state: QueryGraphState) -> QueryGraphState:
        from knowledge.tools.embedding_utils import generate_hybrid_embeddings, get_bge_m3_model
        from knowledge.tools.milvus_utils import (
            get_milvus_client,
            create_hybrid_search_requests,
            execute_hybrid_search_query,
        )

        query = state.get("rewritten_query", "") or state.get("original_query", "")
        item_names = state.get("item_names")
        collection_name = os.getenv("CHUNKS_COLLECTION", "kb_chunks")

        self.log_step("step_1", f"查询向量化: {query}")

        embedding_model = get_bge_m3_model()
        if embedding_model is None:
            self.logger.error("BGE-M3 模型加载失败")
            return {"embedding_chunks": []}

        embeddings = generate_hybrid_embeddings(embedding_model, [query])
        if not embeddings or not embeddings.get("dense"):
            self.logger.error("查询向量化失败")
            return {"embedding_chunks": []}

        filter_expr = build_filter_expr(item_names)
        self.logger.debug(f"过滤表达式: {filter_expr}")

        reqs = create_hybrid_search_requests(
            dense_vector=embeddings["dense"][0],
            sparse_vector=embeddings["sparse"][0],
            dense_params={"metric_type": "IP"},
            sparse_params={"metric_type": "IP"},
            expr=filter_expr,
            limit=self.SEARCH_TOP_K,
        )

        self.log_step("step_2", "执行混合搜索")
        client = get_milvus_client()
        if client is None:
            self.logger.error("Milvus 客户端获取失败")
            return {"embedding_chunks": []}

        res = execute_hybrid_search_query(
            milvus_client=client,
            collection_name=collection_name,
            search_requests=reqs,
            ranker_weights=self.RANKER_WEIGHTS,
            norm_score=True,
            limit=self.RERANK_TOP_K,
            output_fields=self.OUTPUT_FIELDS,
        )

        chunks = res[0] if res else []
        for ch in chunks:
            ch.setdefault("source", "local")
        self.log_step("step_3", f"搜索完成，返回 {len(chunks)} 条结果")

        return {"embedding_chunks": chunks}


_node_instance = SearchEmbeddingNode()


def node_search_embedding(state: QueryGraphState) -> QueryGraphState:
    return _node_instance(state)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    setup_logging()

    print("=" * 60)
    print("向量检索节点测试")
    print("=" * 60)

    test_state = {
        "session_id": "test_001",
        "rewritten_query": "如何使用万用表测量电压？",
        "item_names": [],
        "embedding_chunks": [],
    }

    print(f"查询: {test_state['rewritten_query']}")
    print("-" * 60)

    try:
        result = node_search_embedding(test_state)
        chunks = result.get("embedding_chunks", [])
        print(f"\n检索到 {len(chunks)} 条结果:")
        for i, chunk in enumerate(chunks, 1):
            entity = chunk.get("entity", chunk) if isinstance(chunk, dict) else {}
            content = entity.get("content", "")
            item_name = entity.get("item_name", "未知")
            score = chunk.get("distance", 0)
            print(f"[{i}] 商品: {item_name} | 分数: {score:.4f}")
            print(f"    内容: {content[:80]}...")
    except Exception as e:
        print(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()
