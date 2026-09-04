"""知识图谱查询节点

从用户查询中抽取实体，经 Milvus 对齐后在 Neo4j 中检索相关子图，
最终回填切片文本内容。
"""

import os
import json
import re
import logging
from typing import List, Dict, Any, Set, Tuple, Optional

from knowledge.processor.query_process.base import BaseNode, setup_logging
from knowledge.processor.query_process.state import QueryGraphState
from knowledge.prompts.query.query_prompt import ENTITY_EXTRACT_SYSTEM_PROMPT


class QueryKgNode(BaseNode):
    """知识图谱查询节点。

    流程: LLM 抽取实体 → Milvus 对齐 → Neo4j 种子查找 → 一跳扩展 → 切片关联 → 文本回填
    """

    name = "query_kg"

    # 实体对齐
    KG_ENTITY_ALIGN_MIN_SCORE = 0.7

    # 种子节点
    KG_MAX_SEED_CANDIDATES = 3
    KG_MAX_TOTAL_SEEDS = 30

    # 一跳扩展
    KG_MAX_TRIPLES_PER_SEED = 50
    KG_MAX_TOTAL_TRIPLES = 200

    # 切片获取
    KG_MAX_TOTAL_CHUNKS = 200

    # 节点权重
    W_SEED = 2.0
    W_NEIGHBOR = 1.0

    def process(self, state: QueryGraphState) -> QueryGraphState:
        from knowledge.tools.llm_utils import get_llm_client

        question = state.get("rewritten_query") or state.get("original_query", "")
        item_names = self._clean_item_names(state.get("item_names"))

        for name in item_names:
            question = question.replace(name, "")

        self.log_step("step_1", "LLM 抽取实体")
        llm_client = get_llm_client(response_format=True)
        entities = self._extract_entities(question, llm_client) if llm_client else []

        self.log_step("step_2", "Milvus 对齐实体")
        align_result = self._align_entities(entities, item_names) if entities else {"aligned_entities": [], "alignments": []}
        aligned = align_result.get("aligned_entities", entities)

        self.log_step("step_3", "Neo4j 种子节点 + 扩展一跳")
        seed_nodes = self._find_seed_nodes(aligned, item_names)
        triples = self._expand_one_hop(seed_nodes)

        self.log_step("step_4", "整理输出")
        kg_chunk_hits = self._get_chunk_refs(seed_nodes, triples)
        kg_chunks = self._fetch_chunk_texts(kg_chunk_hits)

        self.logger.info(f"种子节点: {len(seed_nodes)}, 三元组: {len(triples)}, 切片: {len(kg_chunks)}")

        return {
            "kg_chunks": kg_chunks,
            "kg_triples": self._triples_to_docs(triples),
        }

    # ================================================================== #
    #                      预处理                                          #
    # ================================================================== #

    @staticmethod
    def _clean_item_names(item_names) -> List[str]:
        if not item_names:
            return []
        if isinstance(item_names, str):
            return [item_names.strip()] if item_names.strip() else []
        seen: Set[str] = set()
        return [
            s for x in item_names
            if (s := str(x).strip()) and s not in seen and not seen.add(s)
        ]

    # ================================================================== #
    #                      LLM 实体抽取                                    #
    # ================================================================== #

    def _extract_entities(self, question: str, llm_client) -> List[str]:
        from langchain_core.messages import SystemMessage, HumanMessage

        try:
            resp = llm_client.invoke([
                SystemMessage(content=ENTITY_EXTRACT_SYSTEM_PROMPT),
                HumanMessage(content=f"用户问题：{question}"),
            ])

            raw = (resp.content or "").strip()
            # 过滤 LLM 输出的 advisor 咨询/评审文本
            cleaned = re.sub(r'\[Advisor consultation.*?\]', '', raw, flags=re.DOTALL)
            cleaned = re.sub(r'\[Advisor review\]', '', cleaned)
            cleaned = re.sub(r'\[End of advisor consultation.*?\]', '', cleaned, flags=re.DOTALL)
            cleaned = cleaned.strip()

            # 清洗 markdown 围栏
            cleaned = re.sub(r'```json\s*', '', cleaned)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            cleaned = cleaned.strip()

            # 逐 JSON 对象尝试（LLM 可能输出重复 JSON）
            for m in re.finditer(r'\{[^{}]*"entities"[^{}]*\}', cleaned, re.DOTALL):
                candidate = m.group()
                try:
                    data = json.loads(candidate)
                    entities = list({
                        e.strip() for e in data.get("entities", []) if e.strip()
                    })
                    self.logger.info(f"抽取到 {len(entities)} 个实体: {entities}")
                    return entities
                except (JSONDecodeError, ValueError):
                    continue

            # 兜底：直接尝试解析
            data = json.loads(cleaned)
            entities = list({
                e.strip() for e in data.get("entities", []) if e.strip()
            })
            self.logger.info(f"抽取到 {len(entities)} 个实体: {entities}")
            return entities
        except Exception as e:
            self.logger.error(f"实体抽取失败: {e}")
            return []

    # ================================================================== #
    #                      Milvus 实体对齐                                 #
    # ================================================================== #

    def _align_entities(
        self, entities: List[str], item_names: List[str], top_k: int = 5,
    ) -> Dict[str, Any]:
        from knowledge.tools.embedding_utils import generate_hybrid_embeddings, get_bge_m3_model
        from knowledge.tools.milvus_utils import (
            get_milvus_client, create_hybrid_search_requests, execute_hybrid_search_query,
        )

        collection = os.getenv("ENTITY_NAME_COLLECTION", "kb_graph_entity_names")
        client = get_milvus_client()
        min_score = float(os.getenv("KG_ENTITY_ALIGN_MIN_SCORE", str(self.KG_ENTITY_ALIGN_MIN_SCORE)))
        expr = self._build_filter_expr(item_names)

        embedding_model = get_bge_m3_model()
        if embedding_model is None:
            self.logger.error("BGE-M3 模型加载失败")
            return {"aligned_entities": entities, "alignments": []}

        try:
            emb = generate_hybrid_embeddings(embedding_model, entities)
        except Exception as e:
            self.logger.error(f"Embedding 生成失败: {e}")
            return {"aligned_entities": entities, "alignments": []}

        if not emb or not emb.get("dense"):
            return {"aligned_entities": entities, "alignments": []}

        alignments: List[Dict] = []
        aligned: List[str] = []
        seen: Set[str] = set()

        for idx, entity in enumerate(entities):
            dense = emb["dense"][idx]
            sparse = emb["sparse"][idx]

            try:
                reqs = create_hybrid_search_requests(
                    dense_vector=dense,
                    sparse_vector=sparse,
                    dense_params={"metric_type": "COSINE"},
                    sparse_params={"metric_type": "IP"},
                    expr=expr,
                    limit=top_k,
                )

                res = execute_hybrid_search_query(
                    milvus_client=client,
                    collection_name=collection,
                    search_requests=reqs,
                    ranker_weights=(0.5, 0.5),
                    norm_score=True,
                    output_fields=["entity_name", "item_name"],
                )

                best = self._pick_best_hit(res[0] if res else [], min_score)

                if best:
                    name = best["entity"]["entity_name"]
                    if name not in seen:
                        seen.add(name)
                        aligned.append(name)
                    alignments.append({
                        "original": entity,
                        "aligned": name,
                        "score": best["distance"],
                    })
                else:
                    alignments.append({
                        "original": entity,
                        "aligned": None,
                        "reason": "no_hit",
                    })
            except Exception as e:
                alignments.append({
                    "original": entity,
                    "aligned": None,
                    "reason": f"error:{e}",
                })

        self.logger.info(f"对齐后实体: {aligned}")
        return {"aligned_entities": aligned, "alignments": alignments}

    @staticmethod
    def _pick_best_hit(hits: List[Dict], min_score: float) -> Optional[Dict]:
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            score = hit.get("distance", 0)
            entity = hit.get("entity", {})
            if entity.get("entity_name") and score >= min_score:
                return hit
        return None

    # ================================================================== #
    #                      Neo4j 种子节点查找                               #
    # ================================================================== #

    def _find_seed_nodes(
        self, entities: List[str], item_names: List[str],
    ) -> List[Dict]:
        if not entities or not item_names:
            return []

        try:
            from knowledge.tools.neo4j_utils import get_neo4j_driver

            driver = get_neo4j_driver()
            if driver is None:
                return []

            seeds: List[Dict] = []
            seen: Set[Tuple[str, str]] = set()

            with driver.session() as session:
                for name in entities:
                    rows = session.execute_read(
                        self._tx_find_seeds, name, item_names, self.KG_MAX_SEED_CANDIDATES,
                    )

                    for s in rows:
                        key = (s["item_name"], s["name"])
                        if key not in seen:
                            seen.add(key)
                            seeds.append(s)

                        if len(seeds) >= self.KG_MAX_TOTAL_SEEDS:
                            break

                    if len(seeds) >= self.KG_MAX_TOTAL_SEEDS:
                        break

            return seeds
        except Exception as e:
            self.logger.error(f"Neo4j 种子查询异常: {e}")
            return []

    @staticmethod
    def _tx_find_seeds(tx, name: str, item_names: List[str], limit: int):
        seeds = tx.run("""
            MATCH (n:Entity)
            WHERE n.name = $name AND n.item_name IN $item_names
            RETURN n.name AS name, n.item_name AS item_name
            LIMIT $limit
        """, name=name, item_names=item_names, limit=limit).data()

        if seeds:
            return seeds

        return tx.run("""
            MATCH (n:Entity)
            WHERE n.name IS NOT NULL
              AND toLower(n.name) CONTAINS toLower($name)
              AND n.item_name IN $item_names
            RETURN n.name AS name, n.item_name AS item_name
            LIMIT $limit
        """, name=name, item_names=item_names, limit=limit).data()

    # ================================================================== #
    #                      一跳扩展                                        #
    # ================================================================== #

    def _expand_one_hop(self, seed_nodes: List[Dict]) -> List[Dict]:
        if not seed_nodes:
            return []

        try:
            from knowledge.tools.neo4j_utils import get_neo4j_driver

            driver = get_neo4j_driver()
            if driver is None:
                return []

            triples: List[Dict] = []
            seen: Set[Tuple[str, ...]] = set()

            with driver.session() as session:
                for s in seed_nodes:
                    rows = session.execute_read(
                        self._tx_expand_triples,
                        s["name"], s["item_name"], self.KG_MAX_TRIPLES_PER_SEED,
                    )

                    for tr in rows:
                        key = (tr["item_name"], tr["head"], tr["rel"], tr["tail"])
                        if key not in seen:
                            seen.add(key)
                            triples.append(tr)

                        if len(triples) >= self.KG_MAX_TOTAL_TRIPLES:
                            break

                    if len(triples) >= self.KG_MAX_TOTAL_TRIPLES:
                        break

            return triples
        except Exception as e:
            self.logger.error(f"Neo4j 扩展异常: {e}")
            return []

    @staticmethod
    def _tx_expand_triples(tx, seed_name: str, item_name: str, limit: int):
        rows = tx.run("""
            MATCH (seed:Entity {name: $seed, item_name: $item_name})
            CALL {
              WITH seed
              MATCH (seed)-[r]->(nbr:Entity)
              WHERE type(r) <> 'MENTIONED_IN'
                AND nbr.item_name = $item_name
              RETURN seed.name AS head, type(r) AS rel, nbr.name AS tail

              UNION

              WITH seed
              MATCH (nbr:Entity)-[r]->(seed)
              WHERE type(r) <> 'MENTIONED_IN'
                AND nbr.item_name = $item_name
              RETURN nbr.name AS head, type(r) AS rel, seed.name AS tail
            }
            RETURN head, rel, tail LIMIT $limit
        """, seed=seed_name, item_name=item_name, limit=limit).data()

        return [
            {"head": r["head"], "rel": r["rel"],
             "tail": r["tail"], "item_name": item_name}
            for r in rows
        ]

    # ================================================================== #
    #                      获取关联切片                                     #
    # ================================================================== #

    def _get_chunk_refs(
        self, seed_nodes: List[Dict], triples: List[Dict],
    ) -> List[Dict[str, Any]]:
        nodes = self._build_weighted_nodes(seed_nodes, triples)
        if not nodes:
            return []

        try:
            from knowledge.tools.neo4j_utils import get_neo4j_driver

            driver = get_neo4j_driver()
            if driver is None:
                return []

            with driver.session() as session:
                rows = session.run("""
                    UNWIND $nodes AS n
                    MATCH (e:Entity {name: n.name, item_name: n.item_name})
                          -[:MENTIONED_IN]->(c:Chunk {item_name: n.item_name})
                    WITH c, sum(n.w) AS score, count(DISTINCT e) AS cnt
                    RETURN c.id AS chunk_id, c.item_name AS item_name,
                           score, cnt
                    ORDER BY score DESC, cnt DESC, chunk_id ASC
                    LIMIT $limit
                """, nodes=nodes, limit=self.KG_MAX_TOTAL_CHUNKS).data()

            return [
                {
                    "id": None,
                    "distance": float(r.get("score", 0)),
                    "entity": {
                        "chunk_id": str(r["chunk_id"]),
                        "item_name": str(r["item_name"]),
                    },
                }
                for r in rows
            ]
        except Exception as e:
            self.logger.error(f"切片引用查询异常: {e}")
            return []

    def _build_weighted_nodes(
        self, seed_nodes: List[Dict], triples: List[Dict],
    ) -> List[Dict[str, Any]]:
        weights: Dict[Tuple[str, str], float] = {}

        for s in seed_nodes or []:
            key = (s["item_name"], s["name"])
            weights[key] = max(weights.get(key, 0), self.W_SEED)

        for tr in triples or []:
            it = tr["item_name"]
            for n in (tr["head"], tr["tail"]):
                key = (it, n)
                weights[key] = max(weights.get(key, 0), self.W_NEIGHBOR)

        return [
            {"item_name": it, "name": n, "w": w}
            for (it, n), w in weights.items()
        ]

    # ================================================================== #
    #                      Milvus 文本回填                                 #
    # ================================================================== #

    def _fetch_chunk_texts(self, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        from knowledge.tools.milvus_utils import fetch_chunks_by_chunk_ids

        if not hits:
            return []

        collection = os.getenv("CHUNKS_COLLECTION", "kb_chunks")

        chunk_ids = list({
            int(str(h["entity"]["chunk_id"]))
            for h in hits
            if h.get("entity", {}).get("chunk_id") is not None
        })

        if not chunk_ids:
            return []

        try:
            rows = fetch_chunks_by_chunk_ids(
                collection_name=collection,
                chunk_ids=chunk_ids,
                output_fields=["chunk_id", "content", "title", "item_name"],
            )
        except Exception as e:
            self.logger.error(f"Milvus 回填异常: {e}")
            rows = []

        row_map = {
            str(r["chunk_id"]): r
            for r in (rows or [])
            if r.get("chunk_id") is not None
        }

        result = []
        for h in hits:
            ent = h.get("entity", {})
            row = row_map.get(str(ent.get("chunk_id")))
            if row:
                merged = dict(row)
                if ent.get("item_name") and not merged.get("item_name"):
                    merged["item_name"] = ent["item_name"]
                result.append(merged)

        self.logger.info(f"回填完成: {len(result)} 条切片")
        return result

    # ================================================================== #
    #                      三元组转文本                                     #
    # ================================================================== #

    @staticmethod
    def _triples_to_docs(triples: List[Dict]) -> List[str]:
        seen: Set[str] = set()
        docs: List[str] = []

        for tr in triples:
            h, r, t = tr.get("head", ""), tr.get("rel", ""), tr.get("tail", "")
            if not all([h, r, t]):
                continue
            it = tr.get("item_name", "")
            doc = f"[{it}] {h} -({r})-> {t}" if it else f"{h} -({r})-> {t}"
            if doc not in seen:
                seen.add(doc)
                docs.append(doc)

        return docs

    @staticmethod
    def _build_filter_expr(item_names: Optional[List[str]]) -> Optional[str]:
        if not item_names:
            return None
        quoted = ", ".join(f'"{v}"' for v in item_names)
        return f"item_name in [{quoted}]"


_node_instance = QueryKgNode()


def node_query_kg(state: QueryGraphState) -> QueryGraphState:
    return _node_instance(state)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    try:
        setup_logging()
    except Exception:
        import logging
        logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("知识图谱查询节点测试")
    print("=" * 60)

    test_state = {
        "original_query": "RS-12数字万用表怎么测电压？",
        "rewritten_query": "RS-12数字万用表怎么测电压？",
        "item_names": ["RS-12数字万用表"],
    }

    print(f"查询: {test_state['rewritten_query']}")
    print(f"商品: {test_state['item_names']}")
    print("-" * 60)

    try:
        result = node_query_kg(test_state)

        print(f"\n[实体] {result.get('kg_triples', [])}")
        chunks = result.get("kg_chunks", [])
        print(f"\n[切片] 共 {len(chunks)} 条:")
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"  [{i}] {chunk.get('item_name', '?')} | {chunk.get('content', '')[:80]}...")
    except Exception as e:
        print(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()
