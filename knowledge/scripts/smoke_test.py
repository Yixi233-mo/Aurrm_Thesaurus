#!/usr/bin/env python3
"""Quick smoke test for run_query"""
import sys
sys.path.insert(0, r"E:\work_space\掌柜智库\002")

from knowledge.processor.query_process.main_graph import run_query

result = run_query(
    "平安银行2026年第一季度报告的主要财务数据有哪些？",
    "eval_test_001", [], False
)

print("answer_len:", len(result.get("answer", "")))
print("reranked_docs:", len(result.get("reranked_docs", [])))
print("sources:", len(result.get("sources") or []))
print("item_names:", result.get("item_names"))
print("---ANSWER PREVIEW---")
print((result.get("answer", "") or "")[:1500])
print("---SOURCES---")
for i, s in enumerate(result.get("sources") or []):
    print(f"[{i+1}]", s.get("title") or s.get("source"), "| score:", s.get("score") or s.get("rerank_score"))
