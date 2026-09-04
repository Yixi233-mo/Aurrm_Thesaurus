#!/usr/bin/env python3
"""
RAG 知识库抽样验证脚本

对 17 个金融文件进行 15 题抽样问答验证，覆盖 6 个维度。
输出结构化 JSON 报告。
"""
import sys
import os
import json
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

# ==================== 路径设置 ====================
SCRIPT_DIR = Path(__file__).resolve().parent
KNOWLEDGE_DIR = SCRIPT_DIR.parent
PROJECT_DIR = KNOWLEDGE_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from knowledge.processor.query_process.main_graph import run_query

# ==================== 测试问题集 ====================
TEST_QUESTIONS = [
    # --- 核心概念 (20%) ---
    {
        "id": "Q01",
        "dimension": "核心概念",
        "question": "什么是 ETF 基金？它有哪些主要特点？"
    },
    {
        "id": "Q02",
        "dimension": "核心概念",
        "question": "货币基金和债券基金有什么区别？"
    },
    # --- 具体产品 (25%) ---
    {
        "id": "Q03",
        "dimension": "具体产品",
        "question": "平安银行2026年第一季度报告中的主要财务数据有哪些？"
    },
    {
        "id": "Q04",
        "dimension": "具体产品",
        "question": "华夏债券投资基金的投资范围是什么？"
    },
    {
        "id": "Q05",
        "dimension": "具体产品",
        "question": "招商银行2026年第一季度的营收情况如何？"
    },
    # --- 机制原理 (20%) ---
    {
        "id": "Q06",
        "dimension": "机制原理",
        "question": "指数基金的跟踪误差是怎么产生的？如何降低跟踪误差？"
    },
    {
        "id": "Q07",
        "dimension": "机制原理",
        "question": "开放式基金和封闭式基金的份额运作机制有什么不同？"
    },
    # --- 对比辨析 (15%) ---
    {
        "id": "Q08",
        "dimension": "对比辨析",
        "question": "股票型基金、债券型基金和货币市场基金的风险等级和预期收益有什么不同？"
    },
    {
        "id": "Q09",
        "dimension": "对比辨析",
        "question": "公募基金和私募基金在投资者准入门槛上有何区别？"
    },
    # --- 实操流程 (10%) ---
    {
        "id": "Q10",
        "dimension": "实操流程",
        "question": "投资者申购基金一般有哪些步骤？需要注意什么？"
    },
    {
        "id": "Q11",
        "dimension": "实操流程",
        "question": "购买银行理财产品前需要做哪些风险测评？"
    },
    # --- 边界测试 (10%) ---
    {
        "id": "Q12",
        "dimension": "边界测试",
        "question": "请问如何开户炒股？具体流程是什么？",
        "expect_no_hit": True
    },
    {
        "id": "Q13",
        "dimension": "边界测试",
        "question": "2025年中国GDP增速是多少？",
        "expect_no_hit": False
    },
    {
        "id": "Q14",
        "dimension": "边界测试",
        "question": "基金分红有哪些方式？对投资者有什么影响？",
        "expect_no_hit": False
    },
    {
        "id": "Q15",
        "dimension": "边界测试",
        "question": "如何计算基金的收益率？",
        "expect_no_hit": False
    },
]


def run_single_query(question: str, session_id: str, delay: float = 2.0) -> Dict[str, Any]:
    """执行单条查询，返回结构化结果"""
    result = run_query(question, session_id, [], False)

    answer = result.get("answer", "") or ""
    reranked_docs = result.get("reranked_docs", []) or []
    kg_triples = result.get("kg_triples", []) or []

    # 从 reranked_docs 提取来源信息
    sources = []
    seen_sources = set()
    for doc in reranked_docs:
        src = doc.get("source", "")
        title = doc.get("title", "")
        chunk_id = doc.get("chunk_id", "")
        score = doc.get("score")
        source_key = f"{src}:{chunk_id}"
        if source_key not in seen_sources:
            seen_sources.add(source_key)
            sources.append({
                "source": src,
                "title": title,
                "chunk_id": chunk_id,
                "score": score,
                "content_preview": (doc.get("content", "") or "")[:200].replace("\n", " "),
            })

    return {
        "answer": answer,
        "answer_length": len(answer),
        "sources": sources,
        "source_count": len(sources),
        "reranked_docs_count": len(reranked_docs),
        "kg_triples_count": len(kg_triples),
    }


def judge_quality(question_data: Dict, result: Dict) -> Dict[str, Any]:
    """对单题回答质量进行初步评估"""
    qid = question_data["id"]
    is_boundary = question_data.get("expect_no_hit", False)

    answer = result.get("answer", "")
    source_count = result.get("source_count", 0)
    sources = result.get("sources", [])
    reranked_count = result.get("reranked_docs_count", 0)

    # 1. 命中判断
    if is_boundary:
        if source_count == 0 and ("无法回答" in answer or "抱歉" in answer or "没有找到" in answer or "超出" in answer or "不在" in answer):
            quality = "correct_reject"
            reason = "正确识别为知识库外问题"
        elif source_count == 0 and len(answer) < 50:
            quality = "correct_reject"
            reason = "无检索结果，回答为空"
        else:
            quality = "hallucination_risk"
            reason = f"边界问题返回了内容（sources={source_count}, answer_len={len(answer)}）"
    else:
        if source_count == 0 and reranked_count == 0:
            quality = "miss"
            reason = "未检索到任何相关文档"
        elif source_count == 0 and reranked_count > 0:
            quality = "partial"
            reason = f"有reranked_docs({reranked_count})但sources未正确提取"
        elif source_count > 0 and len(answer) > 100:
            quality = "hit"
            reason = f"命中 {source_count} 个来源，生成了 {len(answer)} 字符回答"
        elif source_count > 0 and len(answer) <= 100:
            quality = "partial"
            reason = f"命中来源但回答过短({len(answer)}字符)"
        else:
            quality = "unknown"
            reason = "无法判断"

    # 2. 归因
    if quality in ("miss",):
        if reranked_count == 0:
            diagnosis = "检索问题：未召回相关文档（可能切片不覆盖/检索词不匹配/向量相似度不足）"
        else:
            diagnosis = "生成问题：有召回但回答为空"
    elif quality == "partial":
        diagnosis = "部分命中：可能需要调整提示词或上下文预算"
    elif quality == "hallucination_risk":
        diagnosis = "幻觉风险：边界问题被错误回答，需加强拒答提示词"
    else:
        diagnosis = "正常"

    return {
        "quality": quality,
        "reason": reason,
        "diagnosis": diagnosis,
    }


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = KNOWLEDGE_DIR / "logs" / f"rag_eval_{ts}.json"

    results = []
    stats = {
        "total": len(TEST_QUESTIONS),
        "hit": 0,
        "partial": 0,
        "miss": 0,
        "correct_reject": 0,
        "hallucination_risk": 0,
        "boundary_tests": sum(1 for q in TEST_QUESTIONS if q.get("expect_no_hit")),
    }

    print(f"RAG 抽样验证开始 | 问题数: {len(TEST_QUESTIONS)} | 输出: {output_path}")
    print("=" * 70)

    for i, q in enumerate(TEST_QUESTIONS):
        qid = q["id"]
        session_id = f"eval_{ts}_{qid}"

        print(f"\n[{i+1}/{len(TEST_QUESTIONS)}] {qid} [{q['dimension']}]")
        print(f"  问题: {q['question']}")

        # 执行查询
        try:
            query_result = run_single_query(q["question"], session_id)
        except Exception as e:
            print(f"  ERROR: {e}")
            query_result = {
                "answer": f"ERROR: {e}",
                "answer_length": 0,
                "sources": [],
                "source_count": 0,
                "reranked_docs_count": 0,
                "kg_triples_count": 0,
            }

        # 质量评估
        judgment = judge_quality(q, query_result)

        # 更新统计
        qkey = judgment["quality"]
        if qkey in stats:
            stats[qkey] += 1

        # 记录结果
        record = {
            "id": qid,
            "dimension": q["dimension"],
            "question": q["question"],
            "expect_no_hit": q.get("expect_no_hit", False),
            "answer": query_result["answer"][:3000] if query_result["answer"] else "",
            "answer_length": query_result["answer_length"],
            "sources": query_result["sources"],
            "source_count": query_result["source_count"],
            "reranked_docs_count": query_result["reranked_docs_count"],
            "quality": judgment["quality"],
            "reason": judgment["reason"],
            "diagnosis": judgment["diagnosis"],
        }
        results.append(record)

        # 打印摘要
        quality_icon = {
            "hit": "HIT", "partial": "PARTIAL", "miss": "MISS",
            "correct_reject": "REJECT", "hallucination_risk": "HALLUC"
        }.get(judgment["quality"], "?")
        print(f"  结果: [{quality_icon}] sources={query_result['source_count']}, "
              f"reranked={query_result['reranked_docs_count']}, "
              f"answer_len={query_result['answer_length']}")
        print(f"  评估: {judgment['reason']}")

        # 速率限制：避免 LLM 429
        if i < len(TEST_QUESTIONS) - 1:
            time.sleep(3.0)

    # ==================== 汇总统计 ====================
    effective_total = stats["total"] - stats["boundary_tests"]
    hit_count = stats["hit"] + stats["partial"]
    miss_count = stats["miss"]

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_questions": stats["total"],
        "boundary_tests": stats["boundary_tests"],
        "effective_questions": effective_total,
        "hit": stats["hit"],
        "partial": stats["partial"],
        "miss": stats["miss"],
        "correct_reject": stats["correct_reject"],
        "hallucination_risk": stats["hallucination_risk"],
        "hit_rate": f"{(stats['hit'] / effective_total * 100):.1f}%" if effective_total > 0 else "N/A",
        "effective_hit_rate": f"{((stats['hit'] + stats['partial']) / effective_total * 100):.1f}%" if effective_total > 0 else "N/A",
    }

    print("\n" + "=" * 70)
    print("汇总:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # ==================== 保存报告 ====================
    report = {
        "meta": {
            "project": "金融知识库 RAG 验证",
            "generated_at": ts,
            "environment": {
                "python": "D:/acaconda/envs/knowledge/python.exe (3.10.20)",
                "llm": "step-router-v1 (api.hcnsec.cn)",
                "milvus": "http://192.168.2.169:19530",
                "neo4j": "bolt://192.168.2.169:7687",
                "bge_m3_device": "cuda:0",
                "reranker": "BAAI/bge-reranker-large (cuda:0)",
            },
            "note": "中文输出在 Git Bash 终端可能显示乱码（GBK编码），但文件以 UTF-8 保存，内容正确。",
        },
        "summary": summary,
        "issues_found": [
            {
                "severity": "high",
                "issue": "answer_output.py 缺少 set_task_sources 导入",
                "file": "knowledge/processor/query_process/nodes/answer_output.py",
                "fix": "已修复：from knowledge.tools.task_utils import set_task_result, set_task_sources",
            },
            {
                "severity": "high",
                "issue": "task_utils.py 使用未导入的 Any 类型",
                "file": "knowledge/tools/task_utils.py",
                "fix": "已修复：from typing import Any, Dict, List",
            },
            {
                "severity": "medium",
                "issue": "非流式查询 sources 返回为空",
                "detail": "run_query 直接从 state 返回，但 sources 被 set_task_sources 写入 task_utils 内存字典，未被合并到 state 中",
                "fix": "建议在 answer_output.py 的 process 方法中，将 self._last_sources 写入 state['sources']",
            },
            {
                "severity": "medium",
                "issue": "HyDE 节点频繁触发 429 限流",
                "detail": "LLM 并发限制 10，4 路召回并行时容易超出",
                "fix": "建议增加 LLM 调用队列/信号量，限制并发数为 5-8",
            },
            {
                "severity": "low",
                "issue": "知识图谱召回实体数为 0",
                "detail": "query_kg 返回 0 实体/0 关系，可能是图谱数据不足或实体对齐不匹配",
                "fix": "检查知识图谱导入是否完整，实体链接是否覆盖常见金融产品名",
            },
        ],
        "results": results,
    }

    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n报告已保存: {output_path}")
    return report, output_path


if __name__ == "__main__":
    report, path = main()
