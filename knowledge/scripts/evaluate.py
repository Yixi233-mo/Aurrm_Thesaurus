#!/usr/bin/env python3
"""
金融知识库项目 - 全面评估脚本

逐项测试所有核心组件，生成评估报告。
"""
import sys
import os
import json
import time
import traceback
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR.parent))
os.environ['PYTHONPATH'] = str(PROJECT_DIR.parent)

from knowledge.core import env

results = {"timestamp": datetime.now().isoformat(), "tests": [], "summary": {}}

def test(name, func):
    entry = {"name": name, "status": "unknown", "message": "", "duration": 0}
    start = time.time()
    try:
        ok, msg = func()
        entry["status"] = "pass" if ok else "fail"
        entry["message"] = msg
    except Exception as e:
        entry["status"] = "error"
        entry["message"] = f"{type(e).__name__}: {e}"
    entry["duration"] = round(time.time() - start, 2)
    results["tests"].append(entry)
    icon = "OK" if entry["status"] == "pass" else "FAIL"
    print(f"  [{icon}] {name}: {entry['message'][:80]} ({entry['duration']}s)")
    return entry["status"] == "pass"

# ==================== 1. 环境变量 ====================
def check_env():
    checks = {
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "OPENAI_API_BASE": bool(os.getenv("OPENAI_API_BASE")),
        "LLM_DEFAULT_MODEL": os.getenv("LLM_DEFAULT_MODEL", "NOT SET"),
        "MILVUS_URL": bool(os.getenv("MILVUS_URL")),
        "CHUNKS_COLLECTION": bool(os.getenv("CHUNKS_COLLECTION")),
        "NEO4J_URI": bool(os.getenv("NEO4J_URI")),
        "NEO4J_USERNAME": bool(os.getenv("NEO4J_USERNAME")),
        "NEO4J_PASSWORD": bool(os.getenv("NEO4J_PASSWORD")),
        "MONGO_URL": bool(os.getenv("MONGO_URL")),
        "MINIO_ENDPOINT": bool(os.getenv("MINIO_ENDPOINT")),
        "MINERU_KEY": bool(os.getenv("MINERU_KEY")),
        "BGE_M3_PATH": bool(os.getenv("BGE_M3_PATH")),
        "BGE_DEVICE": os.getenv("BGE_DEVICE", "NOT SET"),
    }
    missing = [k for k, v in checks.items() if not v]
    msg = f"{len(checks) - len(missing)}/{len(checks)} configured"
    if missing:
        msg += f", missing: {missing}"
    return len(missing) == 0, msg

# ==================== 2. Milvus ====================
def check_milvus():
    from knowledge.tools.milvus_utils import get_milvus_client
    client = get_milvus_client()
    if not client:
        return False, "Client creation failed"
    cols = client.list_collections()
    return True, f"Connected, {len(cols)} collections: {cols}"

# ==================== 3. Neo4j ====================
def check_neo4j():
    from knowledge.tools.neo4j_utils import get_neo4j_driver
    driver = get_neo4j_driver()
    with driver.session() as s:
        r = s.run("RETURN 1 as n").data()
    return True, f"Connected, test query: {r}"

# ==================== 4. MongoDB ====================
def check_mongo():
    from knowledge.tools.mongo_history_utils import HistoryMongoTool
    tool = HistoryMongoTool()
    return True, f"Connected, db={tool.db_name}"

# ==================== 5. MinIO ====================
def check_minio():
    from knowledge.tools.minio_utils import get_minio_client
    mc = get_minio_client()
    if not mc:
        return False, "Client creation failed"
    return True, "Connected"

# ==================== 6. LLM ====================
def check_llm():
    from knowledge.tools.llm_utils import get_llm_client
    llm = get_llm_client()
    if not llm:
        return False, "Client creation failed"
    resp = llm.invoke("你好，请用一句话回复")
    content = resp.content.strip()
    if not content:
        return False, "Empty response"
    return True, f"Model responded ({len(content)} chars)"

# ==================== 7. BGE-M3 ====================
def check_bge_m3():
    from knowledge.tools.embedding_utils import get_bge_m3_model
    ef = get_bge_m3_model()
    if not ef:
        return False, "Model loading failed"
    vecs = ef.encode_documents(["test query"])
    dense_dim = len(vecs["dense"][0])
    sparse_nnz = len(vecs["sparse"].data)
    if dense_dim != 1024:
        return False, f"Wrong dense dim: {dense_dim}"
    return True, f"Dense={dense_dim}, Sparse nnz={sparse_nnz}"

# ==================== 8. 导入图 ====================
def check_import_graph():
    from knowledge.processor.import_process.main_graph import kb_import_app
    if not kb_import_app:
        return False, "Graph compilation failed"
    return True, "Compiled successfully"

# ==================== 9. 查询图 ====================
def check_query_graph():
    from knowledge.processor.query_process.main_graph import query_app
    if not query_app:
        return False, "Graph compilation failed"
    return True, "Compiled successfully"

# ==================== 10. Milvus 数据量 ====================
def check_milvus_data():
    from knowledge.tools.milvus_utils import get_milvus_client
    client = get_milvus_client()
    if not client:
        return False, "No client"
    cols = client.list_collections()
    info = {}
    for col in cols:
        try:
            cnt = client.get_collection_stats(col).get("row_count", 0)
            info[col] = cnt
        except Exception:
            info[col] = "error"
    total = sum(v for v in info.values() if isinstance(v, int))
    msg = f"Total {total} records across {len(cols)} collections"
    return True, msg

# ==================== 11. 全链路查询测试 ====================
def check_full_query():
    from knowledge.processor.query_process.main_graph import run_query
    result = run_query("平安银行2026年第一季度报告", "eval_test", [], False)
    answer = result.get("answer", "")
    chunks = result.get("reranked_docs", [])
    item_names = result.get("item_names", [])
    msg = f"item_names={item_names}, reranked_docs={len(chunks)}, answer_len={len(answer)}"
    if not chunks and not answer:
        return False, f"No results retrieved. {msg}"
    return True, msg

# ==================== 主流程 ====================
print("=" * 60)
print("  金融知识库项目评估")
print("=" * 60)
print()

all_pass = True
all_pass &= test("[1] 环境变量", check_env)
all_pass &= test("[2] Milvus 连接", check_milvus)
all_pass &= test("[3] Neo4j 连接", check_neo4j)
all_pass &= test("[4] MongoDB 连接", check_mongo)
all_pass &= test("[5] MinIO 连接", check_minio)
all_pass &= test("[6] LLM 调用", check_llm)
all_pass &= test("[7] BGE-M3 向量化", check_bge_m3)
all_pass &= test("[8] 导入图编译", check_import_graph)
all_pass &= test("[9] 查询图编译", check_query_graph)
all_pass &= test("[10] Milvus 数据检查", check_milvus_data)
all_pass &= test("[11] 全链路查询", check_full_query)

# ==================== 汇总 ====================
passed = sum(1 for t in results["tests"] if t["status"] == "pass")
failed = sum(1 for t in results["tests"] if t["status"] == "fail")
errors = sum(1 for t in results["tests"] if t["status"] == "error")
results["summary"] = {"total": len(results["tests"]), "pass": passed, "fail": failed, "error": errors, "all_pass": all_pass}

print()
print("=" * 60)
print(f"  结果: {passed} pass, {failed} fail, {errors} error")
print("=" * 60)

# ==================== 保存报告 ====================
report_dir = PROJECT_DIR / "logs"
report_dir.mkdir(exist_ok=True)
ts = datetime.now().strftime("%Y%m%d_%H%M%S")

json_path = report_dir / f"eval_report_{ts}.json"
json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

# Markdown report
md_lines = [
    "# 金融知识库项目评估报告",
    f"",
    f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    f"",
    f"## 汇总",
    f"",
    f"| 指标 | 数值 |",
    f"|------|------|",
    f"| 总测试项 | {len(results['tests'])} |",
    f"| 通过 | {passed} |",
    f"| 失败 | {failed} |",
    f"| 错误 | {errors} |",
    f"| 整体状态 | {'ALL PASS' if all_pass else 'HAS ISSUES'} |",
    f"",
    f"## 详细结果",
    f"",
    f"| # | 测试项 | 状态 | 消息 | 耗时(s) |",
    f"|---|--------|------|------|---------|",
]
for i, t in enumerate(results["tests"], 1):
    icon = {"pass": "PASS", "fail": "FAIL", "error": "ERROR"}.get(t["status"], "?")
    md_lines.append(f"| {i} | {t['name']} | {icon} | {t['message'][:60]} | {t['duration']} |")

md_lines += ["", "---", ""]
md_path = report_dir / f"eval_report_{ts}.md"
md_path.write_text("\n".join(md_lines), encoding="utf-8")

print(f"\nJSON report: {json_path}")
print(f"MD report:   {md_path}")
