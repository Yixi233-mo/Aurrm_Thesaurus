# 璇玑金策

> **AURUM THESAURUS** — 基于 RAG 与知识图谱的金融知识库智能问答系统

通过向量检索 + 知识图谱 + Web 搜索的多路召回策略，实现对金融文档（产品说明书、招募说明书、年报、公告等）的精准问答。

## 技术栈

| 层级   | 技术                                       | 说明               |
| ---- | ---------------------------------------- | ---------------- |
| 前端   | React 19 + TypeScript + Vite 8 + Tailwind CSS v4 | SPA 单页应用         |
| 后端   | FastAPI                                  | 双 API 服务架构       |
| 编排   | LangGraph                                | 工作流状态机           |
| 向量库  | Milvus                                   | BGE-M3 稠密+稀疏混合检索 |
| 图数据库 | Neo4j                                    | 金融知识图谱           |
| 文档存储 | MongoDB                                  | 对话历史             |
| 对象存储 | MinIO                                    | 文件存储             |
| LLM  | Step-Router v1                           | 大语言模型            |

## 快速启动

```bash
# 1. 进入项目根目录
cd knowledge

# 2. 激活虚拟环境
conda activate knowledge

# 3. 启动前端（需要 Node.js 18+）
cd front/src
npm install && npm run dev

# 4. 启动导入服务（:8000）
cd ../..
uvicorn knowledge.api.import_router:app --host 0.0.0.0 --port 8000 --reload

# 5. 启动查询服务（:8001）
uvicorn knowledge.api.query_router:app --host 0.0.0.0 --port 8001 --reload
```

前端访问 http://localhost:5173（Vite 代理到后端），或访问构建产物 http://localhost:8001/。

## 项目结构

```
knowledge/
├── api/                    # FastAPI 入口（双服务）
│   ├── import_router.py    # 文件上传 + 导入状态查询 (:8000)
│   └── query_router.py     # 问答 + SSE 流式 + 历史记录 (:8001)
├── core/                   # 跨层基础设施
│   ├── env.py              # .env 统一加载 + torch 兼容补丁
│   ├── deps.py             # Milvus / Neo4j / MinIO 单例
│   └── paths.py            # 路径常量
├── processor/              # LangGraph 工作流
│   ├── import_process/     # 导入流程（8 节点）
│   └── query_process/      # 查询流程（10 节点）
├── services/               # 业务编排层
│   ├── file_import_service.py
│   └── task_service.py
├── tools/                  # 底层工具（DB 客户端 / LLM / 嵌入 / 重排序 / SSE）
├── schemas/                # Pydantic 请求/响应模型
├── prompts/                # LLM 提示词模板
├── front/                  # 前端 SPA
│   └── src/
│       ├── index.html      # HTML 入口（含皮肤预加载）
│       ├── src/
│       │   ├── api/        # HTTP 客户端 + SSE Hook
│       │   ├── store/      # Zustand 状态管理
│       │   ├── components/ # 通用 UI 组件
│       │   ├── pages/      # Chat / Import 页面
│       │   └── index.css   # Tailwind + 三皮肤系统
│       └── public/         # 静态资源
├── scripts/                # 运维 / 验证脚本
├── test/                   # 测试 & 测试数据
├── docs/                   # 补充文档
├── logs/                   # 运行日志 & RAG 评估报告
├── data/                   # 运行时数据（上传文件 / 缓存）
└── .agent/                 # Agent 工作记录
```

## 核心流程

```
导入流程（8 节点）
  entry → pdf_to_md → md_img → document_split →
  item_name_recognition → bge_embedding → import_milvus → knowledge_graph → END

查询流程（10 节点）
  item_name_confirm
    ├── (已有答案) ──────────────────> answer_output
    └── (无答案) ──> multi_search
                       ├── search_embedding     (向量检索)
                       ├── search_embedding_hyde (HyDE)
                       ├── query_kg            (知识图谱)
                       └── web_search_mcp      (Web 搜索)
                              │
                              ▼
                           join → rrf → rerank → answer_output → END
```

## 皮肤系统

三套皮肤并行支持，通过 CSS 自定义属性切换：

| 皮肤       | 标识                  | 风格           |
| -------- | ------------------- | ------------ |
| 砂金博弈（暗色） | `skin-gambit-dark`  | 暖棕底 + 柔金强调   |
| 砂金博弈（亮色） | `skin-gambit-light` | 骨白背景 + 深色侧边栏 |
| 璇玑金策（亮星） | `skin-xuanji`       | 薰衣草紫 + 流金    |

## License

MIT
