#!/bin/bash
# 数据导入验证：对 5 类文档各发 1 个抽样问题，保存结果到 verify_result.json

BASE="http://127.0.0.1:8001"
RESULT="E:/work_space/掌柜智库/002/knowledge/scripts/verify_result.json"

questions=(
  "上市公司年报|请介绍华夏债券基金的基本情况和业绩表现"
  "基金产品|什么是 ETF 基金？它有哪些特点？"
  "宏观经济&政策|近年来中国货币政策的方向是什么？"
  "用户FAQ|理财产品有哪些风险等级？"
  "银行理财&风险揭示书|购买银行理财产品的风险揭示要点有哪些？"
)

echo "[" > "$RESULT"
first=true

for item in "${questions[@]}"; do
  IFS='|' read -r category question <<< "$item"
  echo "  [$category] $question"

  # 提交查询
  session=$(curl -s -X POST "$BASE/query" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"$question\",\"is_stream\":true}" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

  # 收集 SSE（最多 120 秒）
  answer=""
  sources="[]"
  start=$(date +%s)
  while true; do
    # 用 timeout 命令限制单次 curl 为 5 秒
    chunk=$(timeout 5 curl -s -N "$BASE/stream/$session" 2>/dev/null | grep -E "^(event:|data:)" | head -20)
    [ -z "$chunk" ] && continue

    event_type=$(echo "$chunk" | grep "^event:" | head -1 | sed 's/event: *//')
    data_line=$(echo "$chunk" | grep "^data:" | head -1)

    if [ "$event_type" = "delta" ]; then
      delta=$(echo "$data_line" | sed 's/^data: *//' | python3 -c "import sys,json; print(json.load(sys.stdin).get('delta',''))" 2>/dev/null)
      answer="$answer$delta"
    elif [ "$event_type" = "final" ]; then
      sources=$(echo "$data_line" | sed 's/^data: *//' | python3 -c "import sys,json; print(json.load(sys.stdin).get('sources',[]))" 2>/dev/null)
      break
    fi

    now=$(date +%s)
    if [ $((now - start)) -gt 120 ]; then
      echo "    TIMEOUT after 120s"
      break
    fi
  done

  answer_len=${#answer}
  source_count=$(echo "$sources" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")

  if [ "$first" = true ]; then
    first=false
  else
    echo "," >> "$RESULT"
  fi

  python3 -c "
import json
item = {
    'category': '$category',
    'question': '''$question''',
    'ok': $answer_len > 0,
    'answer_len': $answer_len,
    'source_count': $source_count,
    'sources': json.loads('''$sources''')[:5]
}
# 简单转义（实际应使用更 robust 的方法）
print(json.dumps(item, ensure_ascii=False), end='')
" >> "$RESULT"

  echo "    answer_len=$answer_len sources=$source_count"
done

echo "" >> "$RESULT"
echo "]" >> "$RESULT"
echo ""
echo "Results saved to $RESULT"
python3 -c "
import json
with open('$RESULT', encoding='utf-8') as f:
    data = json.load(f)
total = len(data)
passed = sum(1 for x in data if x['ok'])
print(f'passed={passed}/{total}')
for x in data:
    status = 'OK' if x['ok'] else 'FAIL'
    print(f'  [{status}] {x[\"category\"]}: answer_len={x[\"answer_len\"]} sources={x[\"source_count\"]}')
"
