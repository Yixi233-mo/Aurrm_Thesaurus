# 金融知识库项目 - 快速理解文档

> 生成时间: 2026-09-02 | 最后更新: 2026-09-04 | 基于: 需求说明 + 项目状态报告 + 源码分析

---

## 一、项目概述

### 1.1 项目定位

**璇玑金策（AURUM THESAURUS）** 是一个面向金融领域的 RAG（检索增强生成）知识库系统，通过向量检索 + 知识图谱 + Web 搜索的多路召回策略，实现对金融文档的精准问答。

### 1.2 品牌系统

当前项目承载双品牌资产并行：

| 属性 | 砂金博弈 | 璇玑金策（AURUM THESAURUS） |
|------|---------|---------------------------|
| **品牌名称** | 砂金博弈 | 璇玑金策 |
| **英文名称** | — | AURUM THESAURUS |
| **核心意象** | 砂金筹码 × 博弈策略 | 璇玑（古代天文仪器）— 精算与策谋 + 金策 — 金融智慧 |
| **品牌调性** | 博弈 · 策略 · 财富 | 优雅 · 精密 · 智慧 · 深邃 · 策算 |
| **核心文案** | 砂金筹码落，检索万变归真知 | **"璇玑转，金策出，万变归真知。"** |
| **视觉气质** | 暖棕底 × 柔金 × 骨白 | 薰衣草紫 × 流金 × 极光青 |

> 注：「砂金博弈」全部视觉规范作为品牌资产完整保留，前端通过三套皮肤并行支持。

### 1.3 三皮肤系统

前端通过 CSS 自定义属性 + `data-skin` 属性实现三套皮肤切换：

| 皮肤标识 | 名称 | 激活方式 | 说明 |
|---------|------|---------|------|
| `skin-gambit-dark` | 砂金博弈（暗色） | 默认 `:root` | 暖棕底 + 柔金强调 |
| `skin-gambit-light` | 砂金博弈（亮色） | `html.light` class | 骨白背景 + 深色侧边栏 |
| `skin-xuanji` | 璇玑金策（亮星） | `html[data-skin="xuanji"]` | 薰衣草紫 + 流金/极光青双色 |

切换组件 `ThemeToggle.tsx` 渲染三按钮组，用户选择持久化到 `localStorage`，页面加载时 `index.html` 内联脚本提前应用。

**CSS 变量契约（当前实际值）**：

| 变量 | 砂金暗色 | 砂金亮色 | 璇玑亮星 | 用途 |
|------|---------|---------|---------|------|
| `--skin-bg-base` | `#2C2420` | `#F7F3EE` | `#9A90AD` | 全局背景 |
| `--skin-bg-card` | `#3D322C` | `#FFFFFF` | `#ADA3C0` | 卡片背景 |
| `--skin-bg-input` | `#1F1916` | `#FFFFFF` | `#7C728D` | 输入框背景 |
| `--skin-text-primary` | `#EDE6DB` | `#1A1A1A` | `#1A1626` | 正文/标题 |
| `--skin-text-secondary` | `#A89A8C` | `#6B6B6B` | `#4A4460` | 辅助文字 |
| `--skin-text-muted` | `#6B6058` | `#A8A09A` | `#6E6880` | 弱化文字 |
| `--skin-border` | `rgba(196,168,106,0.25)` | `#E8E0D6` | `rgba(26,22,38,0.10)` | 边框/分割线 |
| `--skin-accent` | `#C4A86A` | `#C49A6C` | `#6A6380` | 交互色（选中/链接/进度） |
| `--skin-accent-hover` | `#D9BF8A` | `#DCAE7A` | `#8A83A0` | 悬停/聚焦强调色 |
| `--skin-accent-warm` | `#C4A86A` | `#C49A6C` | `#C9A96E` | 品牌强调色（标题/Logo/装饰） |
| `--skin-accent-warm-hover` | `#D9BF8A` | `#DCAE7A` | `#DDC08A` | 品牌悬停强调色 |
| `--skin-sidebar-bg` | `#1F1916` | `#1A4A50` | `#7D738A` | 侧边栏背景 |
| `--skin-sidebar-text` | `#CCC1B2` | `#E8E4D9` | `#201C2E` | 侧边栏文字 |

> **设计说明**：璇玑亮星皮肤采用双强调色体系——`--skin-accent`（紫调 `#6A6380`）用于交互态，`--skin-accent-warm`（流金 `#C9A96E`）用于品牌元素。砂金博弈两套皮肤共享暖金色系，`accent-warm` 与 `accent` 同值。

为兼容旧组件，`index.css` 将 `--skin-*` 映射为 `--theme-*` / `--sidebar-*` 语义变量。所有 markdown 渲染样式、滚动条、光标、动效均已改为引用 `--skin-*` 变量。

### 1.4 色彩系统

#### 砂金博弈（暗色 · 暖棕调）

| 角色 | 色值 | 说明 |
|------|------|------|
| **全局背景** | `#2C2420` | 暖棕底，醇厚沉稳 |
| **卡片背景** | `#3D322C` | 略浅暖棕 |
| **输入框背景** | `#1F1916` | 深棕 |
| **主文字** | `#EDE6DB` | 暖白 |
| **辅助文字** | `#A89A8C` | 暖灰 |
| **强调色（柔金）** | `#C4A86A` | 暖调金色 |
| **高亮金** | `#D9BF8A` | 悬停点亮 |
| **边框** | `rgba(196,168,106,0.25)` | 柔金边 |

#### 砂金博弈（亮色）

| 角色 | 色值 | 说明 |
|------|------|------|
| **全局背景** | `#F7F3EE` | 暖白纸色 |
| **卡片背景** | `#FFFFFF` | 纯白 |
| **侧边栏背景** | `#1A4A50` | 深孔雀蓝，品牌点缀 |
| **主文字** | `#1A1A1A` | 深灰 |
| **强调色（琥珀金）** | `#C49A6C` | 暖调琥珀 |
| **边框** | `#E8E0D6` | 米灰边框 |

#### 璇玑金策（亮星 · 薰衣草紫）

| 角色 | 色值 | 说明 |
|------|------|------|
| **全局背景** | `#9A90AD` | 薰衣草紫，明亮通透 |
| **卡片背景** | `#ADA3C0` | 略浅紫调 |
| **输入框背景** | `#7C728D` | 深紫调 |
| **侧边栏背景** | `#7D738A` | 中紫调 |
| **主文字** | `#1A1626` | 深紫黑 |
| **辅助文字** | `#4A4460` | 紫灰 |
| **交互色（紫调）** | `#6A6380` | 选中/链接/进度 |
| **品牌强调色（流金）** | `#C9A96E` | 标题/Logo/装饰线 |
| **边框** | `rgba(26,22,38,0.10)` | 淡边框 |

### 1.5 字体系统

| 层级 | 字体 | 字重 | 用途 |
|------|------|------|------|
| **Display** | `"Playfair Display", serif` | Bold (700) | 主标题、品牌名 |
| **Heading** | `"Playfair Display", serif` | SemiBold (600) | 区块标题 |
| **Body** | `"Inter", sans-serif` | Regular (400) | 正文内容 |
| **Caption** | `"Inter", sans-serif` | Light (300) | 脚注、辅助信息 |

字体通过 `index.html` 的 Google Fonts 引入，CSS 变量 `--font-display` / `--font-sans` 暴露给组件使用。

### 1.6 符号系统

| 符号 | 使用场景 | 实现方式 | 适用皮肤 |
|------|---------|---------|---------|
| 同心圆环 | Logo 元素 | SVG 双圆环 + 书本图标 | 全部 |
| ♠ ♥ ♦ ♣ | 装饰水印 | 独立 `<span>` | 仅砂金博弈 |
| 星轨弧线 | Logo 装饰 | SVG 弧线 | 仅璇玑金策 |

约束：每屏花色/装饰不超过 3 处。

### 1.7 动效系统

不依赖 Framer Motion，使用 CSS `@keyframes` + Tailwind `transition` / `animate-*` 实现：

| 场景 | 实现 | 触发时机 |
|------|------|---------|
| 页面入场 | `fade-in-up`（opacity + translateY） | 组件挂载 |
| 卡片悬停 | `hover:shadow` + `hover:-translate-y-1` | `onMouseEnter` |
| 按钮点击 | `active:scale-95` | `onClick` |
| 加载/处理中 | `animate-pulse` + 进度条 | SSE 流式阶段 |
| 打字指示器 | `blink-cursor`（光标动画） | AI 生成中 |
| 星辉微光 | `shimmer`（渐变位移动画） | 卡片/区域强调 |

### 1.8 技术栈（实际）

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 19.2.8 | UI 框架 |
| TypeScript | 6.0.2 | 类型安全 |
| Vite | 8.2.2 | 构建工具 |
| Tailwind CSS | v4.3.3 | 样式系统 |
| Zustand | 5.x | 状态管理 |
| react-router-dom | 7.18.3 | 路由 |
| react-markdown | 10.1.0 | Markdown 渲染 |
| react-dropzone | 20.1.1 | 文件上传 |

> 注：品牌文档中的 React 18 / Tailwind 3 / Framer Motion 为历史版本参考，实际项目已升级至上述版本。动画通过 CSS + Tailwind 过渡实现，不引入 Framer Motion。

### 1.9 三皮肤涉及文件清单

| 层级 | 文件 | 变更内容 |
|------|------|---------|
| 基础 | `front/src/index.html` | 标题「璇玑金策」；内联脚本支持 `data-skin` 预加载 |
| 基础 | `front/src/src/index.css` | `:root` / `html.light` / `html[data-skin]` 三层皮肤变量；markdown / 滚动条 / 光标 / 动效全量适配 |
| 组件 | `front/src/src/components/ThemeToggle.tsx` | 三按钮皮肤选择器，localStorage 持久化 |
| 布局 | `front/src/src/components/Sidebar.tsx` | 品牌名；Logo 同心圆 + 璇玑星轨弧线；条件渲染花色装饰；标语切换 |
| 页面 | `front/src/src/pages/Chat.tsx` | 欢迎语；璇玑星轨分隔线；Header 引入 ThemeToggle |
| 页面 | `front/src/src/pages/Import.tsx` | Header 引入 ThemeToggle |
| 布局 | `front/src/src/App.tsx` | 根背景使用 `bg-[var(--skin-bg-base)]` |

---

## 二、为什么需要这个项目

传统方式下，用户需要手动翻阅大量 PDF（产品说明书、招募说明书、风险揭示书、年报、公告、FAQ 等）才能找到答案。本项目将这些文档自动转化为结构化知识，通过 RAG + 知识图谱技术实现精准问答，大幅降低信息获取成本。

---

## 三、技术架构全景

```
┌─────────────────────────────────────────────────────────────┐
│              前端 (React 19 + TypeScript + Vite)              │
│          /front/ → SPA（智能问答 + 文档导入）                 │
│          React Router | Tailwind CSS | Zustand               │
└──────────────┬──────────────────┬────────────────────────────┘
               │                  │
     ┌─────────▼──────┐  ┌───────▼─────────┐
     │  Import 服务   │  │  Query 服务     │
     │  :8000         │  │  :8001          │
     │  FastAPI       │  │  FastAPI        │
     └────────┬───────┘  └───────┬────────┘
              │                  │
     ┌────────▼──────────────────▼────────┐
     │      Processor 层 (LangGraph)        │
     │  ┌─────────────┐  ┌──────────────┐  │
     │  │ 导入流程图   │  │ 查询流程图    │  │
     │  │ 8 个节点     │  │ 8 个节点     │  │
     │  └─────────────┘  └──────────────┘  │
     └────────┬──────────────────┬────────┘
              │                  │
     ┌────────▼──────┐  ┌───────▼────────┐
     │   Tools 层     │  │   LLM 层        │
     │  10+ 工具模块  │  │  Step-Router    │
     └────────┬──────┘  └───────┬────────┘
              │                  │
     ┌────────▼──────────────────▼────────┐
     │              数据层                   │
     │  Milvus │ Neo4j │ MongoDB │ MinIO   │
     └────────────────────────────────────┘
```

### 3.1 核心流程对比

| 维度   | 导入流程                 | 查询流程                     |
| ---- | -------------------- | ------------------------ |
| 入口   | 文件上传                 | 自然语言查询                   |
| 编排   | LangGraph StateGraph | LangGraph StateGraph     |
| 节点数  | 8                    | 8                        |
| 核心步骤 | PDF→MD→切分→向量化→入库→建图谱 | 实体确认→4路召回→RRF融合→重排序→生成答案 |
| 输出   | 结构化知识切片 + 知识图谱       | 带引用的自然语言回答               |
| 端口   | 8000                 | 8001                     |

### 3.2 导入流程节点

```
entry → pdf_to_md → md_img → document_split →
item_name_recognition → bge_embedding → import_milvus → knowledge_graph → END
```

### 3.3 查询流程节点

```
item_name_confirm
    ├── (已有答案) ──────────────────> answer_output
    └── (无答案) ──> multi_search
                       ├── search_embedding (向量检索)
                       ├── search_embedding_hyde (HyDE)
                       ├── query_kg (知识图谱)
                       └── web_search_mcp (Web搜索)
                              │
                              ▼
                           join → rrf → rerank → answer_output → END
```

### 3.4 多路召回策略

采用 **RRF (Reciprocal Rank Fusion)** 融合 4 路召回结果：
1. **向量检索**: BGE-M3 稠密+稀疏混合检索
2. **HyDE**: 假设文档检索（生成假设答案再检索）
3. **知识图谱**: Neo4j 实体关系查询
4. **Web 搜索**: MCP 协议外部搜索

---

## 四、已导入数据情况

| 分类         | 文件数    | 切片数     |
| ---------- | ------ | ------- |
| 上市公司年报     | 3      | 150     |
| 基金产品       | 3      | 40      |
| 宏观经济&政策    | 2      | 94      |
| 用户FAQ      | 6      | 146     |
| 银行理财&风险揭示书 | 3      | 78      |
| **总计**     | **17** | **508** |

---

## 五、环境配置（当前生产环境）

虚拟环境：`D:\acaconda\envs\knowledge`

| 组件      | 地址                                       | 状态              |
| ------- | ---------------------------------------- | --------------- |
| LLM     | https://api.hcnsec.cn/v1 (step-router-v1) | 正常              |
| Milvus  | http://192.168.2.169:19530               | 正常 (5集合, 5288条) |
| Neo4j   | bolt://192.168.2.169:7687                | 正常              |
| MongoDB | mongodb://192.168.2.169:27017/kb001      | 正常              |
| MinIO   | 192.168.2.169:9000                       | 正常              |
| BGE-M3  | CUDA加载, 1024维稠密+稀疏                       | 正常              |

---

## 六、项目目录结构

```
knowledge/
├── api/                  # API 路由
│   ├── query_router.py   # 查询服务 (:8001)
│   └── import_router.py  # 导入服务 (:8000)
├── core/                 # 核心配置
│   ├── env.py            # .env 统一加载
│   ├── deps.py           # 依赖注入单例
│   └── paths.py          # 路径常量
├── processor/            # LangGraph 工作流
│   ├── import_process/   # 导入流程（8节点）
│   └── query_process/    # 查询流程（8节点）
├── tools/                # 工具函数（12个模块）
│   ├── llm_utils.py      # LLM 客户端（含并发控制）
│   ├── milvus_utils.py   # 向量库操作
│   ├── neo4j_utils.py    # 图数据库操作
│   ├── embedding_utils.py # BGE-M3 向量嵌入
│   └── ...
├── schemas/              # Pydantic 数据模型
├── services/             # 业务服务
├── prompts/              # 提示词模板
├── front/                # 前端（React 19 SPA）
│   ├── dist/             # 构建产物（静态文件）
│   └── src/
│       ├── index.html    # HTML 入口
│       ├── src/
│       │   ├── types/    # TypeScript 类型定义
│       │   ├── api/      # API 客户端 + SSE Hook
│       │   ├── store/    # Zustand 状态管理
│       │   ├── components/ # UI 组件
│       │   ├── pages/    # 页面组件（Chat, Import）
│       │   ├── hooks/    # 自定义 Hooks
│       │   ├── App.tsx   # 根组件 + Router
│       │   └── index.css # Tailwind CSS + 三皮肤系统
│       └── public/       # 静态资源（favicon等）
├── scripts/              # 脚本工具
├── test/                 # 测试
├── logs/                 # 运行日志 & RAG评估报告
├── data/                 # 数据目录
│   ├── uploads/          # 上传文件
│   └── cache/            # 缓存文件
├── docs/                 # 补充文档
├── .agent/               # Agent 工作记录
│   ├── prompts/          # Agent 提示词归档
│   ├── sessions/         # 对话摘要/任务记录
│   └── decisions/        # 关键技术决策记录
├── import/               # 项目文档（根目录层级）
│   ├── PROJECT_OVERVIEW.md
│   └── 身份.txt
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 七、已修复的问题

| #    | 问题                        | 解决方案                                     |
| ---- | ------------------------- | ---------------------------------------- |
| 1    | .env 路径问题                 | 创建 `core/env.py` 统一入口，基于文件位置定位           |
| 2    | LLM 兼容性                   | 升级 `langchain-openai` 和 `openai` 到兼容版本   |
| 3    | BGE-M3 加载失败               | 将 `pytorch_model.bin` 转换为 `model.safetensors` 格式，解决 CVE-2025-32434 限制 |
| 4    | Milvus metric_type 不匹配    | 将查询时的 `COSINE` 改为 `IP`，与集合创建时的索引类型保持一致   |
| 5    | 查询路由逻辑                    | 未识别产品时不再返回错误，而是继续通用检索                    |
| 6    | `rerank_max_top_k` 属性名不匹配 | `config.py` 中 `rerank_max_topk` → `rerank_max_top_k`，`rerank_min_topk` → `rerank_min_top_k` |
| 7    | BGE-M3 meta tensor bug | 重写 `_BGE3EmbeddingFunction`，使用 transformers + 自定义加载 colbert_linear/sparse_linear |
| 8    | FlagReranker meta tensor 初始化失败 | 在 `core/env.py` 添加 `ACCELERATE_DISABLE_META_INIT=1` |
| 9    | rerank.py 异常处理 bug | `{**merged_multi_docs}` → `{**doc}` |
| 10   | .env ITEM_MODEL/KG_MODEL 不支持 | `auto` → `step-router-v1` |
| 11   | LLM JSON 解析失败 | item_name_confirm 增加 JSON 围栏清洗 + 首个 JSON 对象提取 |
| 12   | Milvus metric_type 不匹配 | 集合创建用 IP，查询参数统一回 IP |
| 13   | 前端 SPA 路由嵌套报错 | `App.tsx` 与 `main.tsx` 重复使用 `BrowserRouter`，已修复为仅 `App.tsx` 保留路由容器，`main.tsx` 移除嵌套 |
| 14   | query_kg Milvus metric_type 不匹配 | `kb_graph_entity_names` 集合 dense_vector 索引为 COSINE，`_align_entities` 硬编码 IP，已改为 COSINE |
| 15   | BGE-M3 并发竞态条件 | 并行节点同时首次调用 `get_bge_m3_model()` 导致 meta tensor 错误，增加 `threading.Lock` 保证单例安全 |
| 16   | 联网搜索鉴权失败 | DashScope MCP 的 API Key 不匹配，迁移至 Parallel.ai MCP（`streamable_http_client` + `web_search` 工具），无需鉴权 |
| 17   | LLM 429 并发限制 | `llm_utils.py` 增加 `_LLMClientWrapper`（`threading.Semaphore(5)`），包装 `invoke/stream/batch`，全局并发上限控制在 5 |

---

## 八、当前状态

> **基线状态**：2026-09-04 项目基线已建立，Git 仓库已初始化（未提交）。

所有已知阻塞已修复。RAG 抽样验证已完成（15题，命中率 64.3%）。
当前待优化项：
- P0：LLM 451审查拦截（Q04/Q07触发）、边界问题拒答能力（Q12幻觉风险）
- ~~P1：LLM 429并发控制~~ ✅ 已修复（2026-09-04，`_LLMClientWrapper` Semaphore(5)）
- P1：Advisor文本泄漏清洗
- P2：知识图谱召回为0（KG链路待排查）

已验证功能：
- 向量检索 + Reranker 链路正常（14/15题成功召回）
- Web搜索（Parallel.ai MCP）补全通用金融知识
- 结构化输出格式正确（简要结论/主要内容/风险提示/引用来源）
- sources 追溯字段正常工作
- 前端三皮肤系统（砂金博弈暗色/亮色 + 璇玑金策亮星·薰衣草紫）

---

## 九、待办任务清单

### 9.1 近期任务（系统验证与完善）

- [x] **全链路端到端查询测试** — 阻塞已修复，验证完整查询流程
- [x] **流式输出验证** — SSE 流式回答正常渲染
- [x] **多轮对话测试** — 上下文连续追问
- [x] **金融领域提示词优化** — 针对金融场景优化 answer_output 提示词
- [x] **回答模板设计** — 结构化输出（简要结论 / 主要内容 / 风险提示 / 引用来源）
- [ ] **数据导入验证** — 对已导入的 17 个文件进行抽样问答验证

### 9.2 近期任务（金融领域适配）

- [ ] **金融术语解释库** — 从知识库中抽取术语定义
- [ ] **产品对比功能** — 多产品并排对比
- [ ] **风险等级标注** — 在检索结果中高亮风险相关内容
- [x] **来源追溯增强** — SSE `final` 携带 `sources`，前端 `SourcePanel` 可折叠展示引用来源
- [ ] **知识图谱实体类型扩展** — 适配金融领域实体（产品/机构/风险等级等）

### 9.3 远期任务（平台扩展）

- [ ] **净值和行情数据接入** — 对接实时数据源
- [ ] **公告提醒功能** — 新公告自动入库并推送
- [ ] **产品收藏与浏览历史** — 用户个性化功能
- [ ] **风险测评联动** — 对接用户风险测评结果
- [ ] **移动端适配** — 响应式前端
- [ ] **人工客服转接** — 无缝衔接人工服务

---

## 十、关键文件速查

| 功能         | 文件路径                                     |
| ---------- | ---------------------------------------- |
| 导入 API     | `api/import_router.py`                   |
| 查询 API     | `api/query_router.py`                    |
| 导入流程图      | `processor/import_process/main_graph.py` |
| 查询流程图      | `processor/query_process/main_graph.py`  |
| **当前阻塞文件** | 无（已全部修复） |
| 查询配置       | `processor/query_process/config.py`      |
| 答案生成       | `processor/query_process/nodes/answer_output.py` |
| 提示词模板      | `prompts/query/query_prompt.py`          |
| LLM 客户端    | `tools/llm_utils.py`                     |
| 向量检索       | `tools/milvus_utils.py`                  |
| 知识图谱查询     | `tools/neo4j_utils.py`                   |
| 联网搜索（Parallel.ai MCP） | `processor/query_process/nodes/web_search_mcp.py` |
| 环境配置加载     | `core/env.py`                            |
| 皮肤系统       | `front/src/src/index.css` + `ThemeToggle.tsx` |

---

## 十一、快速启动

```bash
# 1. 进入项目根目录（不是 knowledge/）
cd E:\work_space\掌柜智库\002

# 2. 激活虚拟环境
conda activate knowledge   # 虚拟环境路径: D:\acaconda\envs\knowledge

# 3. 前端开发（可选，需要 Node.js 18+）
cd knowledge/front/src
npm install
npm run dev     # → http://localhost:5173
npm run build   # 构建产物输出到 knowledge/front/dist/

# 4. 返回项目根目录并启动导入服务
cd ..\..\..
uvicorn knowledge.api.import_router:app --host 0.0.0.0 --port 8000 --reload

# 5. 启动查询服务（另开终端，同样在项目根目录）
uvicorn knowledge.api.query_router:app --host 0.0.0.0 --port 8001 --reload

# 6. 访问
# 前端 SPA: http://localhost:8001/front/ （或 :8000/front/）
# API 文档: http://localhost:8001/docs
```

---

## 十二、RAG 知识库抽样验证结果（2026-09-03）

### 12.1 验证概况

| 指标 | 数值 |
|------|------|
| 总题数 | 15 |
| 边界测试 | 1（Q12：开户炒股，期望不命中） |
| 有效题目 | 14 |
| 命中（HIT） | 9 |
| 部分命中（PARTIAL） | 3 |
| 未命中（MISS） | 2 |
| 正确拒答（CORRECT_REJECT） | 0 |
| 幻觉风险（HALLUCINATION_RISK） | 1 |
| 命中率 | 64.3% |
| 有效命中率（HIT+PARTIAL） | 85.7% |

> 报告文件：`knowledge/logs/rag_eval_20260903_202139.json`

### 12.2 各维度表现

| 维度 | 题号 | 结果 | 备注 |
|------|------|------|------|
| 核心概念 | Q01 | HIT | ETF定义及特点，861字符，1来源 |
| 核心概念 | Q02 | MISS | LLM 429限流导致失败 |
| 具体产品 | Q03 | HIT | 平安银行Q1财报，1325字符，1来源 |
| 具体产品 | Q04 | PARTIAL | 451审查拦截，仅返回13字符错误信息 |
| 具体产品 | Q05 | MISS | LLM 429限流导致失败 |
| 机制原理 | Q06 | HIT | 跟踪误差，1164字符，1来源 |
| 机制原理 | Q07 | PARTIAL | 451审查拦截，仅返回13字符错误信息 |
| 对比辨析 | Q08 | HIT | 三类型基金风险收益对比，1439字符 |
| 对比辨析 | Q09 | PARTIAL | 2来源但回答仅13字符 |
| 实操流程 | Q10 | HIT | 基金申购步骤，1767字符（含advisor残留） |
| 实操流程 | Q11 | HIT | 风险测评流程，1997字符 |
| 边界测试 | Q12 | HALLUC | 应拒答但返回1081字符详细答案 |
| 边界测试 | Q13 | HIT | 2025 GDP增速，621字符 |
| 边界测试 | Q14 | HIT | 基金分红方式，677字符 |
| 边界测试 | Q15 | HIT | 收益率计算，1848字符（含advisor残留） |

### 12.3 关键发现

**积极发现**
- 向量检索 + Reranker 链路正常，14/15 题成功召回文档（source>0）
- Web 搜索（Parallel.ai MCP）补全了知识库未覆盖的通用金融知识
- 答案质量普遍较高，结构化输出符合预期（简要结论/主要内容/风险提示/引用来源）

**需优化项**
1. **LLM 并发限制**：Q02/Q05 因 `concurrency reached, current: 11, limit: 10` 直接失败。4路召回并行时HyDE/item_name_confirm同时调用LLM容易超限。
2. **LLM 审查拦截（451）**：Q04（基金分红历史）、Q07（开放式/封闭式基金）触发内容审查，导致回答被截断为错误提示。
3. **边界问题拒答能力不足**：Q12（开户炒股）属于知识库外问题，系统未正确识别并拒答，返回了详细的开户流程（幻觉风险）。
4. **Advisor 文本污染**：Q10/Q15 答案中残留了 `<advisor>` 审查计划内容，说明提示词中的advisor机制仍有泄漏。
5. **知识图谱召回为 0**：所有 15 题的 KG 召回均为 0 实体/0 关系，知识图谱链路未发挥实际作用。

### 12.4 优化建议优先级

| 优先级 | 问题 | 建议 |
|--------|------|------|
| P0 | LLM 451审查拦截 | 在 prompt 中增加合规表述，避免敏感词；或增加重试降级策略 |
| P0 | 边界问题拒答 | 在 answer_output prompt 中强化：若检索源均为web且问题超出金融范围，应拒答 |
| P1 | LLM 429并发 | 增加 LLM 调用信号量（Semaphore(5)），控制并发数低于10 |
| P1 | Advisor文本泄漏 | 清洗逻辑覆盖所有advisor标签变体；或在prompt中禁止输出advisor内容 |
| P2 | 知识图谱召回为0 | 检查 Neo4j 实体对齐逻辑，确保金融产品名能被正确链接 |

### 12.5 验收状态

| 验收项 | 状态 |
|--------|------|
| 基础查询流程稳定性 | ⚠️ 待优化（429/451问题） |
| 核心概念回答质量 | ✅ 通过 |
| 具体产品回答质量 | ⚠️ 部分通过（审查问题待解决） |
| 边界问题拒答能力 | ❌ 未通过 |
| 来源追溯准确性 | ✅ 通过 |
| 结构化输出格式 | ✅ 通过（minor advisor泄漏） |

---

## 十三、进度日志

| 日期 | 任务 | 状态 | 备注 |
|------|------|------|------|
| 2026-09-02 | 生成 PROJECT_OVERVIEW.md 项目理解文档 | ✅ 完成 | |
| 2026-09-02 | 修复 rerank.py 配置属性名不匹配 (`rerank_max_topk` → `rerank_max_top_k`) | ✅ 完成 | 验证通过 |
| 2026-09-02 | 修复 BGE-M3 加载失败（pymilvus meta tensor bug） | ✅ 完成 | 重写 `_BGE3EmbeddingFunction`，使用 transformers + 自定义 colbert/sparse 层加载 |
| 2026-09-02 | 修复 FlagReranker meta tensor 初始化失败 | ✅ 完成 | 在 `core/env.py` 添加 `ACCELERATE_DISABLE_META_INIT=1` |
| 2026-09-02 | 修复 rerank.py 异常处理 bug (`{**merged_multi_docs}` → `{**doc}`) | ✅ 完成 | |
| 2026-09-02 | 修复 .env ITEM_MODEL/KG_MODEL (`auto` → `step-router-v1`) | ✅ 完成 | 服务端不支持 `auto` 路由 |
| 2026-09-02 | 修复 LLM JSON 解析失败（item_name_confirm） | ✅ 完成 | 增加 JSON 围栏清洗 + 首个 JSON 对象提取 |
| 2026-09-02 | 修复 Milvus metric_type 不匹配 | ✅ 完成 | 集合创建用 IP，查询参数已统一回 IP |
| 2026-09-02 | 全链路端到端查询测试 | ✅ 通过 | 2/2 查询通过，完整 8 节点流程正常 |
| 2026-09-02 | 修复 query_kg/hyde COSINE metric_type 残留 | ✅ 完成 | 查询节点统一改为 IP，与集合索引一致 |
| 2026-09-02 | 修复 item_name_confirm 未设置 item_names | ✅ 完成 | 未匹配产品时显式设为空列表 |
| 2026-09-02 | 修复 answer_output item_names 缺省 KeyError | ✅ 完成 | 使用 `.get("item_names") or []` 保护 |
| 2026-09-02 | 金融领域提示词优化 | ✅ 完成 | 结构化输出 + 合规约束 + 通俗语言 |
| 2026-09-02 | 流式输出验证 | ✅ 完成 | 后端 SSE + 前端 EventSource 链路验证通过 |
| 2026-09-02 | 多轮对话测试 | ✅ 完成 | 历史记录接入 answer_output 提示词 |
| 2026-09-03 | 来源追溯增强（SourcePanel） | ✅ 完成 | SSE `final` 携带 `sources`，前端新增 `SourcePanel` 组件展示引用来源（标题/来源/url/相关度） |
| 2026-09-03 | LLM advisor 文本污染修复 | ✅ 完成 | answer_output / item_name_confirm / query_kg / search_embedding_hyde 4 个节点增加 regex 清洗 |
| 2026-09-03 | BGE-M3 meta tensor 修复增强 | ✅ 完成 | embedding_utils.py 的 `load_state_dict` 增加 `assign=True` 参数 |
| 2026-09-03 | 数据导入验证（第一轮） | ⚠️ 初步通过 | 5/5 查询返回非空答案（1284/392/735/264/1021 字符），但 sources 均为 0 |
| 2026-09-03 | 数据导入验证（第二轮回归） | ✅ 已修复 | 根因：query_kg.py metric_type 硬编码 IP（应为 COSINE）+ BGE-M3 并发竞态条件 |
| 2026-09-03 | 修复 query_kg Milvus metric_type | ✅ 完成 | `kb_graph_entity_names` 集合 dense_vector 索引为 COSINE，`_align_entities` 硬编码 IP 导致 Milvus 异常 |
| 2026-09-03 | 修复 BGE-M3 并发竞态条件 | ✅ 完成 | `get_bge_m3_model()` 增加 `threading.Lock`，防止并行节点同时初始化 |
| 2026-09-03 | 联网搜索迁移到 Parallel.ai MCP | ✅ 完成 | 替换 DashScope MCP → Parallel.ai MCP（`streamable_http_client` + `web_search` 工具），无需鉴权 |
| 2026-09-03 | 端到端验证（3 查询回归） | ✅ 通过 | 通用/金融/产品三类查询均返回非空答案（2985/846/797 字符），联网搜索返回 10 条 |
| 2026-09-03 | 非流式查询返回 sources | ✅ 完成 | 补充 `task_utils.py` sources 存储；`answer_output.py` 非流式持久化 sources；`query_router.py` `/query` 返回带 `sources` |
| 2026-09-03 | 修复 task_utils.py 缺少 Any 导入 | ✅ 完成 | `_tasks_sources: Dict[str, List[Dict[str, Any]]]` 需要 Any，否则 NameError |
| 2026-09-03 | 修复 answer_output.py 缺少 set_task_sources 导入 | ✅ 完成 | 第 38 行 `set_task_sources(session_id, self._last_sources)` 未导入 |
| 2026-09-03 | 修复 run_query() 返回 sources 为空 | ✅ 完成 | 在 answer_output.py process 末尾增加 `state["sources"] = self._last_sources`；同步更新 QueryGraphState 和 DEFAULT_STATE |
| 2026-09-03 | 前端品牌迁移：砂金博弈 | ✅ 完成 | 10 个前端文件完成品牌风格迁移（深孔雀蓝 + 砂金 + 象牙白 + 暗夜黑） |
| 2026-09-03 | RAG 知识库抽样验证（15题） | ✅ 完成 | 报告 `logs/rag_eval_20260903_202139.json`，命中率 64.3% |
| 2026-09-04 | 修复 LLM 429 并发限制 | ✅ 完成 | `llm_utils.py` 增加 `_LLMClientWrapper`（`threading.Semaphore(5)`），包装 `invoke/stream/batch`，全局并发上限从 10 降至 5 |
| 2026-09-04 | 品牌升级：砂金博弈 → 璇玑金策 | ✅ 完成 | 更新身份.txt、index.html标题、Sidebar/Chat品牌文案；新增三皮肤系统 |
| 2026-09-04 | 前端三皮肤系统实现 | ✅ 完成 | 新增 skin-gambit-dark / skin-gambit-light / skin-xuanji 三套皮肤，CSS变量 + data-skin属性切换 |
| 2026-09-04 | 前端品牌变量体系重构 | ✅ 完成 | index.css新增--skin-*语义变量层，markdown/滚动条/光标/动效全量适配 |
| 2026-09-04 | 项目目录优化 & Git初始化 | ✅ 完成 | 创建.agent/、data/、docs/目录；创建.gitignore；Git仓库初始化（未提交） |
| 2026-09-04 | 三皮肤 CSS 变量全量替换 | ✅ 完成 | 组件层硬编码颜色全面替换为CSS变量引用；璇玑专属装饰元素添加；ThemeToggle 皮肤适配 |
| 2026-09-04 | 项目收尾清理 | ✅ 完成 | 见下方「十三之附录：收尾清理记录」 |

### 十三之附录：收尾清理记录

| 日期 | 操作 | 文件/模块 | 类型 | 说明 |
|------|------|---------|------|------|
| 2026-09-04 | 删除旧版静态文件 | `front/chat.html` | 删除 | 旧版纯 HTML 问答页面，已被 React SPA 取代 |
| 2026-09-04 | 删除旧版静态文件 | `front/import.html` | 删除 | 旧版纯 HTML 导入页面，已被 React SPA 取代 |
| 2026-09-04 | 删除未引用资源 | `front/src/src/assets/hero.png` | 删除 | 测试用占位图，无组件引用 |
| 2026-09-04 | 删除未引用资源 | `front/src/src/assets/react.svg` | 删除 | Vite 模板默认图标，无组件引用 |
| 2026-09-04 | 删除未引用资源 | `front/src/src/assets/vite.svg` | 删除 | Vite 模板默认图标，无组件引用 |
| 2026-09-04 | 删除空目录 | `front/src/src/{types,api,store,components,pages,hooks}` | 删除 | Git bash 花括号展开产生的空目录，误创建于构建过程中 |
| 2026-09-04 | 清理缓存 | 全部 `__pycache__/` 目录（10+ 处） | 删除 | Python 运行缓存，不应入版本控制 |
| 2026-09-04 | 修复路由重定向 | `api/query_router.py` `/chat.html` → `/chat` | 修复 | 旧版重定向指向静态目录，应重定向到 React Router 路由 |
| 2026-09-04 | 修复路由重定向 | `api/import_router.py` `/import.html` → `/import` | 修复 | 同上 |
| 2026-09-04 | 修复启动脚本文案 | `scripts/start_server.py` | 修复 | 访问地址从 `/chat.html`/`/import.html` 更新为 `/chat`/`/import` |
| 2026-09-04 | 修复验证脚本端口 | `scripts/verify_import.sh` | 修复 | 测试地址从 `:8002` 更正为 `:8001`（查询服务端口） |
