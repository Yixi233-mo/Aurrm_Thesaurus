"""HyDE 向量搜索节点

使用 Hypothetical Document Embedding 技术：
先让 LLM 生成假设性文档，再将其与原查询拼接后向量化检索，提升召回质量。
"""

import os
import re
from typing import List, Optional

from knowledge.processor.query_process.base import BaseNode, setup_logging
from knowledge.processor.query_process.state import QueryGraphState
from knowledge.prompts.query.query_prompt import HYDE_PROMPT_TEMPLATE


class SearchEmbeddingHydeNode(BaseNode):
    """HyDE 向量搜索节点。

    流程: LLM 生成假设文档 → 拼接原查询 → 向量化 → 混合检索
    """

    name = "search_embedding_hyde"

    SEARCH_TOP_K = 10
    RERANK_TOP_K = 5
    RANKER_WEIGHTS = (0.5, 0.5)
    OUTPUT_FIELDS = ["chunk_id", "content", "item_name", "title"]

    def process(self, state: QueryGraphState) -> QueryGraphState:
        query = state.get("rewritten_query") or state.get("original_query", "")
        if not query:
            self.logger.error("未找到用户查询")
            return {}

        item_names = state.get("item_names")

        try:
            self.log_step("step_1", "生成假设性文档")
            hyde_doc = self._generate_hyde_doc(query)

            self.log_step("step_2", "执行混合搜索")
            chunks = self._search(query, hyde_doc, item_names)

            self.log_step("step_3", f"搜索完成，返回 {len(chunks)} 条结果")
            return {"hyde_embedding_chunks": chunks}
        except Exception as e:
            self.logger.error(f"HyDE 搜索失败: {e}")
            return {}

    def _generate_hyde_doc(self, query: str) -> str:
        from knowledge.tools.llm_utils import get_llm_client

        llm = get_llm_client()
        prompt = HYDE_PROMPT_TEMPLATE.format(query=query)
        raw = llm.invoke(prompt).content

        # 过滤 LLM 输出的 advisor 咨询/评审文本（Step-Router-v1 会额外输出）
        cleaned = re.sub(r'\[Advisor consultation.*?\]', '', raw, flags=re.DOTALL)
        cleaned = re.sub(r'\[Advisor review\]', '', cleaned)
        cleaned = cleaned.strip()

        return cleaned or raw

    def _search(
        self, query: str, hyde_doc: str,
        item_names: Optional[List[str]] = None,
    ) -> list:
        from knowledge.tools.embedding_utils import generate_hybrid_embeddings, get_bge_m3_model
        from knowledge.tools.milvus_utils import (
            get_milvus_client,
            create_hybrid_search_requests,
            execute_hybrid_search_query,
        )

        combined_text = f"{query} {hyde_doc}"

        embedding_model = get_bge_m3_model()
        if embedding_model is None:
            self.logger.error("BGE-M3 模型加载失败")
            return []

        embeddings = generate_hybrid_embeddings(embedding_model, [combined_text])
        if not embeddings or not embeddings.get("dense"):
            return []

        collection_name = os.getenv("CHUNKS_COLLECTION", "kb_chunks")

        reqs = create_hybrid_search_requests(
            dense_vector=embeddings["dense"][0],
            sparse_vector=embeddings["sparse"][0],
            dense_params={"metric_type": "IP"},
            sparse_params={"metric_type": "IP"},
            expr=self._build_filter_expr(item_names),
            limit=self.SEARCH_TOP_K,
        )

        client = get_milvus_client()
        if client is None:
            return []

        res = execute_hybrid_search_query(
            milvus_client=client,
            collection_name=collection_name,
            search_requests=reqs,
            ranker_weights=self.RANKER_WEIGHTS,
            norm_score=True,
            limit=self.RERANK_TOP_K,
            output_fields=self.OUTPUT_FIELDS,
        )

        return res[0] if res else []

    @staticmethod
    def _build_filter_expr(item_names: Optional[List[str]]) -> Optional[str]:
        if not item_names:
            return None
        quoted = ", ".join(f'"{v}"' for v in item_names)
        return f"item_name in [{quoted}]"


_node_instance = SearchEmbeddingHydeNode()


def node_search_embedding_hyde(state: QueryGraphState) -> QueryGraphState:
    return _node_instance(state)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    setup_logging()

    print("=" * 60)
    print("HyDE 向量搜索节点测试")
    print("=" * 60)

    test_state = {
        "session_id": "test_001",
        "rewritten_query": "如何使用万用表测量电压？",
        "original_query": "如何使用万用表测量电压？",
        "item_names": [],
    }

    print(f"查询: {test_state['rewritten_query']}")
    print("-" * 60)

    result = node_search_embedding_hyde(test_state)
    chunks = result.get("hyde_embedding_chunks", [])
    print(f"\n检索到 {len(chunks)} 条结果:")
    for i, chunk in enumerate(chunks, 1):
        entity = chunk.get("entity", {}) if isinstance(chunk, dict) else {}
        print(f"[{i}] {entity.get('item_name', '?')} | score={chunk.get('distance', 0):.4f}")
        print(f"    {entity.get('content', '')[:80]}...")
