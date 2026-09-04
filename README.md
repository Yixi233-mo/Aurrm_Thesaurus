# 璇玑金策 (AURUM THESAURUS)

基于 RAG 与知识图谱的金融知识库智能问答系统。

> 项目主体代码位于 [knowledge/](knowledge/) 目录下。

## 核心能力

- **多路召回**：向量检索 + HyDE + 知识图谱 + Web 搜索，RRF 融合排序
- **文档导入**：PDF → Markdown → 图片提取 → 文档分块 → 实体识别 → BGE-M3 嵌入 → Milvus + Neo4j
- **流式问答**：SSE 实时推送，LangGraph 工作流编排
- **三套皮肤**：砂金博弈（暗色/亮色）、璇玑金策（亮星）

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript + Vite 8 + Tailwind CSS v4 |
| 后端 | FastAPI（双服务：导入 :8000 / 查询 :8001） |
| 编排 | LangGraph StateGraph |
| 向量库 | Milvus（BGE-M3 稠密+稀疏） |
| 图数据库 | Neo4j |
| 文档存储 | MongoDB |
| 对象存储 | MinIO |
| LLM | Step-Router v1 |

## 快速启动

```bash
cd knowledge
conda activate knowledge
cd front/src && npm install && npm run dev    # 前端 :5173
# 终端 2：
uvicorn knowledge.api.import_router:app --host 0.0.0.0 --port 8000 --reload  # 导入服务
uvicorn knowledge.api.query_router:app --host 0.0.0.0 --port 8001 --reload   # 查询服务
```

前端访问 http://localhost:5173，或构建产物 http://localhost:8001/

## 文档

详见 [knowledge/README.md](knowledge/README.md) 和 [import/PROJECT_OVERVIEW.md](import/PROJECT_OVERVIEW.md)
