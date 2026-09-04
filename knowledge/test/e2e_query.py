# -*- coding: utf-8 -*-
"""全链路端到端查询测试 - knowledge conda env"""
import sys, os
sys.path.insert(0, r"E:\work_space\掌柜智库\002")
os.environ['PYTHONIOENCODING'] = 'utf-8'

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

from knowledge.processor.query_process.main_graph import run_query

QUERIES = [
    ("q1_fund_risk", "这个基金的风险等级是什么"),
    ("q2_wealth", "什么是净值型理财"),
]

PASS = 0
FAIL = 0

for label, q in QUERIES:
    print(f"\n{'='*60}")
    print(f"Test [{label}]: {q}")
    print(f"{'='*60}")
    try:
        result = run_query(query=q, session_id=label, item_names=[], is_stream=False)

        emb = len(result.get("embedding_chunks", []))
        hyde = len(result.get("hyde_embedding_chunks", []))
        kg = len(result.get("kg_chunks", []))
        rrf = len(result.get("rrf_chunks", []))
        rerank = len(result.get("reranked_docs", []))
        answer = result.get("answer", "")

        print(f"  item_names: {result.get('item_names', [])}")
        print(f"  embedding={emb} hyde={hyde} kg={kg} rrf={rrf} rerank={rerank}")
        print(f"  answer_len={len(answer)}")
        print(f"  answer: {answer[:300]}")

        if answer and len(answer) > 10:
            print(f"  PASS")
            PASS += 1
        else:
            print(f"  WARN: answer too short or empty")
            FAIL += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback; traceback.print_exc()
        FAIL += 1

print(f"\n{'='*60}")
print(f"Result: {PASS} passed, {FAIL} failed out of {len(QUERIES)}")
print(f"{'='*60}")
sys.exit(0 if FAIL == 0 else 1)
