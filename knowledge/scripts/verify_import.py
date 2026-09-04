#!/usr/bin/env python3
"""数据导入验证：对 5 类已导入文档各发 1 个抽样问题"""
import json, sys, requests

BASE = "http://127.0.0.1:8001"
RESULT = "E:/work_space/掌柜智库/002/knowledge/scripts/verify_result.json"

QUESTIONS = [
    ("上市公司年报",     "招商银行2026年第一季度的业绩情况如何？"),
    ("基金产品",         "华夏债券投资基金（华夏债券C）的基本情况是什么？"),
    ("宏观经济&政策",    "中国货币政策执行报告的主要内容是什么？"),
    ("用户FAQ",          "ETF基金有哪些特点？投资者需要注意什么？"),
    ("银行理财&风险揭示书", "理财产品风险揭示书的主要内容有哪些？"),
]

results = []

for category, question in QUESTIONS:
    print(f"\n[{category}] {question}", flush=True)
    try:
        resp = requests.post(f"{BASE}/query",
                             json={"query": question, "is_stream": True}, timeout=30)
        resp.raise_for_status()
        session_id = resp.json()["session_id"]
    except Exception as e:
        print(f"  FAILED to submit: {e}", flush=True)
        results.append({"category": category, "question": question, "ok": False, "error": str(e)})
        continue

    answer = ""
    sources = []
    try:
        with requests.get(f"{BASE}/stream/{session_id}", stream=True, timeout=180) as r:
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("event:"):
                    ev = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    try:
                        p = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if ev == "delta":
                        answer += p.get("delta", "")
                    elif ev == "final":
                        sources = p.get("sources", [])
                        break
    except Exception as e:
        print(f"  Stream error: {e}", flush=True)

    ok = bool(answer.strip())
    preview = answer[:500].replace("\n", " ") + ("..." if len(answer) > 500 else "")
    print(f"  answer_len={len(answer)}  sources={len(sources)}", flush=True)
    print(f"  preview: {preview}", flush=True)

    results.append({
        "category": category,
        "question": question,
        "ok": ok,
        "answer_len": len(answer),
        "source_count": len(sources),
        "sources": [
            {k: v for k, v in s.items() if k in ("idx", "source", "title", "score")}
            for s in sources[:5]
        ],
    })

with open(RESULT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
passed = sum(1 for x in results if x["ok"])
print(f"passed={passed}/{len(results)}")
for x in results:
    status = "OK" if x["ok"] else "FAIL"
    print(f"  [{status}] {x['category']}: answer_len={x['answer_len']} sources={x['source_count']}")
