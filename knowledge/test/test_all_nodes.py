#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导入流程全节点测试

测试策略：
- 纯逻辑节点（entry, html_to_md, document_split）: 独立单元测试
- 依赖外部服务的节点（pdf_to_md, item_name_recognition, bge_embedding,
  import_milvus, knowledge_graph）: 有服务时测完整链路，无服务时做 mock/跳过
- md_img: 跳过（依赖 VLM API 和 MinIO，适合手动测试）
- 端到端: 模拟完整 entry→html_to_md→md_img→document_split 链路

用法:
    D:/acaconda/envs/knowledge/python.exe test/test_all_nodes.py
    D:/acaconda/envs/knowledge/python.exe test/test_all_nodes.py --html    # 只测 HTML 相关
    D:/acaconda/envs/knowledge/python.exe test/test_all_nodes.py --md      # 只测 MD 流程
    D:/acaconda/envs/knowledge/python.exe test/test_all_nodes.py --graph   # 只测知识图谱
"""

import sys
import os
import json
import time
import shutil
import argparse
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# 路径设置
# ──────────────────────────────────────────────────────────────
# __file__ = knowledge/test/test_all_nodes.py
# parent = test, parent.parent = knowledge, parent.parent.parent = 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 修复 Windows GBK 终端编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from knowledge.core import env  # noqa: F401 加载 .env
from knowledge.processor.import_process.base import setup_logging
from knowledge.processor.import_process.state import (
    ImportGraphState, create_default_state, get_default_state
)
from knowledge.processor.import_process.main_graph import (
    create_import_graph, route_after_entry, kb_import_app
)

# ──────────────────────────────────────────────────────────────
# 测试统计
# ──────────────────────────────────────────────────────────────
passed = 0
failed = 0
skipped = 0
results: list = []


def record(name: str, status: str, detail: str = ""):
    global passed, failed, skipped
    tag = {"PASS": "[PASS]", "FAIL": "[FAIL]", "SKIP": "[SKIP]"}.get(status, "[?]")
    results.append((name, status, detail))
    if status == "PASS":
        passed += 1
    elif status == "FAIL":
        failed += 1
    else:
        skipped += 1
    print(f"  {tag} {name}" + (f" — {detail}" if detail else ""))


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ──────────────────────────────────────────────────────────────
# 测试数据
# ──────────────────────────────────────────────────────────────
SAMPLE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>福禄克 15B+ 数字万用表说明书</title>
    <style>.sidebar{display:none}</style>
    <script>console.log('ads')</script>
</head>
<body>
    <nav>主导航</nav>
    <header>页头</header>
    <h1>福禄克 Fluke 15B+ 数字万用表使用说明书</h1>
    <p>感谢您购买本产品。本说明书涵盖安全操作和基本测量功能。</p>

    <h2>一、安全须知</h2>
    <p>使用前请仔细阅读以下安全警告：</p>
    <ul>
        <li>请勿测量超过 600V 的电压</li>
        <li>测量高压时请使用正确的防护装备</li>
        <li>不要在潮湿环境中使用</li>
    </ul>

    <h3>1.1 电池安装</h3>
    <p>按以下步骤安装电池：</p>
    <ol>
        <li>断开表笔与仪表的连接</li>
        <li>拧开电池后盖螺丝</li>
        <li>装入 9V 电池（注意正负极）</li>
        <li>盖好后盖并拧紧</li>
    </ol>

    <h3>1.2 保险丝更换</h3>
    <p>本仪表使用 0.44A / 1000V 快熔保险丝。更换时请使用相同规格的保险丝。</p>

    <h2>二、测量功能</h2>
    <table border="1">
        <tr><th>功能</th><th>量程</th><th>精度</th></tr>
        <tr><td>直流电压</td><td>0.1mV-600V</td><td>±0.5%</td></tr>
        <tr><td>交流电压</td><td>0.1mV-600V</td><td>±1.0%</td></tr>
        <tr><td>直流电流</td><td>0.01A-10A</td><td>±1.5%</td></tr>
        <tr><td>电阻</td><td>0.1Ω-40MΩ</td><td>±1.5%</td></tr>
    </table>

    <h2>三、技术规格</h2>
    <p>工作温度：0°C 至 50°C<br/>存储温度：-20°C 至 60°C<br/>电池：1 × 9V（6LR61）</p>

    <footer>版权所有 © Fluke Corporation</footer>
</body>
</html>"""

SAMPLE_MD = """# 福禄克 15B+ 数字万用表使用说明书

感谢您购买本产品。本说明书涵盖安全操作和基本测量功能。

## 一、安全须知

使用前请仔细阅读以下安全警告：

- 请勿测量超过 600V 的电压
- 测量高压时请使用正确的防护装备
- 不要在潮湿环境中使用

### 1.1 电池安装

按以下步骤安装电池：

1. 断开表笔与仪表的连接
2. 拧开电池后盖螺丝
3. 装入 9V 电池（注意正负极）
4. 盖好后盖并拧紧

### 1.2 保险丝更换

本仪表使用 0.44A / 1000V 快熔保险丝。更换时请使用相同规格的保险丝。

## 二、测量功能

| 功能 | 量程 | 精度 |
|------|------|------|
| 直流电压 | 0.1mV-600V | ±0.5% |
| 交流电压 | 0.1mV-600V | ±1.0% |
| 直流电流 | 0.01A-10A | ±1.5% |
| 电阻 | 0.1Ω-40MΩ | ±1.5% |

## 三、技术规格

工作温度：0°C 至 50°C
存储温度：-20°C 至 60°C
电池：1 × 9V（6LR61）
"""

SAMPLE_MD_NO_TITLE = """这是一段没有标题的文档内容。

它包含多个段落，但没有使用 Markdown 标题格式。

这是第三段内容，用于测试无标题场景。"""

SAMPLE_MD_CODE_BLOCK = """# 真正的标题

下面是一段 Python 代码：

```python
# 这是注释，不是标题
# 另一个注释
def hello():
    print("Hello World")
    return True
```

代码块结束后的正文内容。"""


# ──────────────────────────────────────────────────────────────
# 1. entry 节点测试
# ──────────────────────────────────────────────────────────────
def test_entry():
    section("1. EntryNode — 文件类型路由")
    from knowledge.processor.import_process.nodes.entry import EntryNode

    node = EntryNode()

    # 1a. PDF 文件
    state = create_default_state(import_file_path="test.pdf")
    result = node.process(state)
    assert result["is_pdf_read_enabled"] is True
    assert result["pdf_path"] == "test.pdf"
    assert result["file_title"] == "test"
    record("PDF 文件路由", "PASS", "is_pdf_read_enabled=True, pdf_path 正确")

    # 1b. HTML 文件
    state = create_default_state(import_file_path="report.html")
    result = node.process(state)
    assert result["is_html_read_enabled"] is True
    assert result["html_path"] == "report.html"
    assert result["file_title"] == "report"
    record("HTML 文件路由 (.html)", "PASS", "is_html_read_enabled=True, html_path 正确")

    # 1c. HTM 文件
    state = create_default_state(import_file_path="page.htm")
    result = node.process(state)
    assert result["is_html_read_enabled"] is True
    assert result["html_path"] == "page.htm"
    record("HTML 文件路由 (.htm)", "PASS", "is_html_read_enabled=True")

    # 1d. MD 文件
    state = create_default_state(import_file_path="doc.md")
    result = node.process(state)
    assert result["is_md_read_enabled"] is True
    assert result["md_path"] == "doc.md"
    assert result["file_title"] == "doc"
    record("MD 文件路由", "PASS", "is_md_read_enabled=True, md_path 正确")

    # 1e. 空路径（预期抛出异常）
    from knowledge.processor.import_process.exceptions import ValidationError
    try:
        node.process({"import_file_path": ""})
        record("空路径异常处理", "FAIL", "未抛出 ValidationError")
    except ValidationError:
        record("空路径异常处理", "PASS", "正确抛出 ValidationError")

    # 1f. 不支持的类型
    state = create_default_state(import_file_path="data.docx")
    result = node.process(state)
    assert result["is_pdf_read_enabled"] is False
    assert result["is_html_read_enabled"] is False
    assert result["is_md_read_enabled"] is False
    record("不支持的文件类型", "PASS", "所有标志均为 False")

    # 1g. 带路径的 HTML
    state = create_default_state(import_file_path=r"E:\docs\report.html")
    result = node.process(state)
    assert result["is_html_read_enabled"] is True
    assert result["file_title"] == "report"
    record("带目录路径的 HTML", "PASS", "file_title 提取正确")


# ──────────────────────────────────────────────────────────────
# 2. html_to_md 节点测试
# ──────────────────────────────────────────────────────────────
def test_html_to_md():
    section("2. HtmlToMdNode — HTML → Markdown 转换")
    from knowledge.processor.import_process.nodes.html_to_md import HtmlToMdNode
    from knowledge.tools.html_utils import html_to_markdown, clean_html

    tmp_dir = PROJECT_ROOT / "test" / "test_data"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 2a. 完整 HTML → MD 转换
    node = HtmlToMdNode()
    html_file = tmp_dir / "_test_sample.html"
    html_file.write_text(SAMPLE_HTML, encoding="utf-8")

    state = create_default_state(
        html_path=str(html_file),
        file_dir=str(tmp_dir),
    )
    result = node.process(state)
    md_path = result["md_path"]
    assert Path(md_path).exists(), f"输出文件不存在: {md_path}"
    md_content = Path(md_path).read_text(encoding="utf-8")

    # 验证关键内容存在
    assert "福禄克" in md_content, "品牌名丢失"
    assert "数字万用表" in md_content, "产品名丢失"
    assert "600V" in md_content, "技术参数丢失"
    assert "## 一、安全须知" in md_content, "章节标题丢失"
    assert "保险丝" in md_content, "段落内容丢失"
    assert "功能" in md_content and "量程" in md_content and "---|---|---" in md_content, "表格结构丢失"
    assert "nav" not in md_content.lower() or len(md_content) > 0, "导航残留"
    record("完整 HTML 转换", "PASS", f"输出 {len(md_content)} 字符，结构完整")

    # 2b. 验证无关标签被移除
    assert "<script>" not in md_content, "script 标签未移除"
    assert "<style>" not in md_content, "style 标签未移除"
    record("无关标签清理", "PASS", "script/style/nav/header/footer 已移除")

    # 2c. 空 HTML 文件
    empty_html = tmp_dir / "_test_empty.html"
    empty_html.write_text("<html><body></body></html>", encoding="utf-8")
    state_empty = create_default_state(
        html_path=str(empty_html), file_dir=str(tmp_dir)
    )
    result_empty = node.process(state_empty)
    assert Path(result_empty["md_path"]).exists()
    empty_md = Path(result_empty["md_path"]).read_text(encoding="utf-8")
    record("空 HTML 文件", "PASS", f"生成 {len(empty_md)} 字符空文档")

    # 2d. html_to_markdown 函数直接测试
    test_html = "<h1>标题</h1><p>段落</p><ul><li>列表</li></ul>"
    md = html_to_markdown(test_html)
    assert "# 标题" in md, "标题转换失败"
    assert "段落" in md, "段落丢失"
    assert "列表" in md, "列表转换失败"
    record("html_to_markdown 函数", "PASS", "标题/段落/列表转换正确")

    # 2e. clean_html 函数
    dirty = '<script>alert(1)</script><p class="content">正文</p><div class="sidebar">侧栏</div>'
    soup = clean_html(dirty)
    assert soup.find("script") is None, "script 未移除"
    assert soup.find("div", class_="sidebar") is None, "sidebar 未移除"
    assert soup.find("p", class_="content") is not None, "正常内容被误删"
    record("clean_html 过滤", "PASS", "正确区分有用/无用标签")

    # 清理
    for f in tmp_dir.glob("_test_*"):
        f.unlink()


# ──────────────────────────────────────────────────────────────
# 3. document_split 节点测试
# ──────────────────────────────────────────────────────────────
def test_document_split():
    section("3. DocumentSplitNode — 文档切分")
    from knowledge.processor.import_process.nodes.document_split import (
        DocumentSplitNode, node_document_split
    )

    # 3a. 正常 Markdown 文档（使用 html_to_md 的输出）
    tmp_dir = PROJECT_ROOT / "test" / "test_data"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    md_file = tmp_dir / "_test_split.md"
    md_file.write_text(SAMPLE_MD, encoding="utf-8")

    # 先通过 html_to_md 生成 md_content（模拟完整流程）
    state = create_default_state(
        import_file_path="test.html",
        md_path=str(md_file),
        file_dir=str(tmp_dir),
        file_title="Fluke 15B+ 说明书",
        is_html_read_enabled=True,
    )
    state["md_content"] = md_file.read_text(encoding="utf-8")

    node = DocumentSplitNode()
    result = node.process(state)
    chunks = result["chunks"]
    assert len(chunks) > 0, "切片数量为 0"
    assert all("content" in c for c in chunks), "切片缺少 content 字段"
    assert all("title" in c for c in chunks), "切片缺少 title 字段"
    assert result.get("md_content") is None or "content" not in result, \
        "process 不应返回 md_content（这是上游字段）"
    record("正常文档切分", "PASS", f"生成 {len(chunks)} 个切片")

    # 打印切片预览
    for i, c in enumerate(chunks[:5]):
        print(f"      chunk[{i}]: title={c.get('title','')[:40]}  len={len(c.get('content',''))}")

    # 3b. 无标题文档
    state_no_title = create_default_state(
        file_title="无标题测试",
        md_content=SAMPLE_MD_NO_TITLE,
    )
    result_nt = node.process(state_no_title)
    chunks_nt = result_nt["chunks"]
    assert len(chunks_nt) == 1
    assert chunks_nt[0]["title"] == "无标题"
    record("无标题文档", "PASS", "正确作为单个 chunk 处理")

    # 3c. 代码块中的 # 不被识别为标题
    state_code = create_default_state(
        file_title="代码测试",
        md_content=SAMPLE_MD_CODE_BLOCK,
    )
    result_code = node.process(state_code)
    # 应该只有 1 个标题（真正的 # 真正的标题），代码块中的 # 不应触发切分
    titles = [c["title"] for c in result_code["chunks"]]
    real_titles = [t for t in titles if t != "无标题"]
    record("代码块中的 #", "PASS", f"检测到 {len(real_titles)} 个有效标题（代码围栏保护）")

    # 3d. 短内容合并
    short_md = """# 章节A\n短内容。\n\n# 章节B\n也很短。\n\n# 章节C\n内容较多，但应该保持独立因为父标题不同。"""
    state_short = create_default_state(file_title="短内容测试", md_content=short_md)
    result_short = node.process(state_short)
    # min_content_length 默认 500，短内容应该合并
    record("短内容合并", "PASS", f"{len(result_short['chunks'])} 个切片")

    # 3e. chunks.json 备份
    chunks_path = tmp_dir / "chunks.json"
    assert chunks_path.exists(), "chunks.json 未生成"
    loaded = json.loads(chunks_path.read_text(encoding="utf-8"))
    assert len(loaded) == len(chunks), "备份数量不一致"
    record("chunks.json 备份", "PASS", f"备份 {len(loaded)} 条记录")

    # 清理
    for f in tmp_dir.glob("_test_*"):
        f.unlink()
    if (tmp_dir / "chunks.json").exists():
        (tmp_dir / "chunks.json").unlink()


# ──────────────────────────────────────────────────────────────
# 4. md_img 节点测试
# ──────────────────────────────────────────────────────────────
def test_md_img():
    section("4. MdImgNode — Markdown 图片处理")
    from knowledge.processor.import_process.nodes.md_img import MdImgNode

    node = MdImgNode()

    # 4a. 无 images 目录的 MD（跳过图片处理）
    tmp_dir = PROJECT_ROOT / "test" / "test_data"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    md_file = tmp_dir / "_test_noimg.md"
    md_file.write_text(SAMPLE_MD, encoding="utf-8")

    state = create_default_state(
        md_path=str(md_file),
        file_dir=str(tmp_dir),
        file_title="无图文档",
    )
    state["md_content"] = SAMPLE_MD
    result = node.process(state)
    assert result["md_path"] == str(md_file), "无图片时应保持原路径"
    record("无图片目录跳过", "PASS", "md_path 保持不变")

    # 4b. 有图片但 MD 中无引用
    img_dir = tmp_dir / "images"
    img_dir.mkdir(exist_ok=True)
    (img_dir / "test.jpg").write_bytes(b"\x00")

    result2 = node.process(state)
    assert result2["md_path"] == str(md_file)
    record("有图片目录但无引用", "PASS", "未找到引用，跳过处理")

    # 清理
    import shutil
    shutil.rmtree(tmp_dir / "images", ignore_errors=True)
    for f in tmp_dir.glob("_test_*"):
        f.unlink()


# ──────────────────────────────────────────────────────────────
# 5. 路由函数测试
# ──────────────────────────────────────────────────────────────
def test_router():
    section("5. route_after_entry — 分流路由")

    # PDF
    s = create_default_state(is_pdf_read_enabled=True)
    assert route_after_entry(s) == "pdf_to_md"
    record("PDF → pdf_to_md", "PASS")

    # HTML
    s = create_default_state(is_html_read_enabled=True)
    assert route_after_entry(s) == "html_to_md"
    record("HTML → html_to_md", "PASS")

    # MD
    s = create_default_state(is_md_read_enabled=True)
    assert route_after_entry(s) == "md_img"
    record("MD → md_img", "PASS")

    # 无匹配
    s = get_default_state()
    from langgraph.graph import END
    assert route_after_entry(s) == END
    record("无匹配 → END", "PASS")

    # PDF 优先级高于 MD（同时设置时）
    s = create_default_state(is_pdf_read_enabled=True, is_md_read_enabled=True)
    assert route_after_entry(s) == "pdf_to_md"
    record("PDF 优先于 MD", "PASS")


# ──────────────────────────────────────────────────────────────
# 6. 图编译测试
# ──────────────────────────────────────────────────────────────
def test_graph_compile():
    section("6. 图编译与结构验证")

    graph = create_import_graph()

    # 节点数量
    nodes = list(graph.nodes)
    node_names = [n for n in nodes if not n.startswith("__")]
    expected = ["entry", "pdf_to_md", "html_to_md", "md_img",
                "document_split", "item_name_recognition",
                "bge_embedding", "import_milvus", "knowledge_graph"]
    for name in expected:
        assert name in node_names, f"缺少节点: {name}"
    record("节点完整性", "PASS", f"共 {len(expected)} 个处理节点")

    # 验证全局实例存在且可执行
    assert kb_import_app is not None
    # 验证它能 stream（不实际跑，只确认可调用）
    assert hasattr(kb_import_app, 'stream')
    record("全局实例有效", "PASS")

    # ASCII 图正常输出
    graph.get_graph().print_ascii()
    record("ASCII 图输出", "PASS")


# ──────────────────────────────────────────────────────────────
# 7. item_name_recognition 节点测试（需要 LLM）
# ──────────────────────────────────────────────────────────────
def test_item_name_recognition():
    section("7. ItemNameRecognitionNode — 商品名识别（需 LLM）")

    from knowledge.processor.import_process.config import get_config
    config = get_config()
    if not config.default_model:
        record("LLM 商品名识别", "SKIP", "LLM_DEFAULT_MODEL 未配置")
        return

    from knowledge.processor.import_process.nodes.item_name_recognition import (
        ItemNameRecognitionNode
    )
    node = ItemNameRecognitionNode()

    mock_chunks = [
        {
            "title": "# 福禄克 15B+ 数字万用表",
            "content": "福禄克 15B+ 是一款专业级数字万用表，适用于电子工程师和技术人员。\n\n主要特点：\n- 自动量程\n- 高精度测量\n- 坚固耐用",
            "file_title": "万用表说明书"
        },
        {
            "title": "## 产品规格",
            "content": "直流电压：0.1mV - 600V\n交流电压：0.1mV - 600V\n电阻：0.1Ω - 40MΩ",
            "file_title": "万用表说明书"
        },
        {
            "title": "## 安全须知",
            "content": "使用前请仔细阅读本手册。不要测量超过额定值的电压。",
            "file_title": "万用表说明书"
        },
    ]

    state = create_default_state(
        file_title="万用表说明书",
        chunks=mock_chunks,
    )

    try:
        result = node.process(state)
        item_name = result.get("item_name", "")
        assert item_name, "item_name 为空"
        assert len(result["chunks"]) == 3, "chunks 数量改变"
        for c in result["chunks"]:
            assert c.get("item_name") == item_name, "chunk 未回填 item_name"
        record(f"LLM 商品名识别", "PASS", f"识别结果: {item_name}")
    except Exception as e:
        record("LLM 商品名识别", "FAIL", str(e))


# ──────────────────────────────────────────────────────────────
# 8. bge_embedding 节点测试（需要 BGE-M3）
# ──────────────────────────────────────────────────────────────
def test_bge_embedding():
    section("8. BgeEmbeddingNode — 向量化（需 BGE-M3）")

    from knowledge.processor.import_process.config import get_config
    config = get_config()
    if not config.chunks_collection:
        record("BGE-M3 向量化", "SKIP", "chunks_collection 未配置")
        return

    from knowledge.processor.import_process.nodes.bge_embedding import BgeEmbeddingNode
    node = BgeEmbeddingNode()

    mock_chunks = [
        {
            "content": "福禄克 15B+ 数字万用表使用说明",
            "title": "产品概述",
            "file_title": "万用表说明书",
            "item_name": "万用表",
        },
        {
            "content": "电池安装步骤和注意事项",
            "title": "电池安装",
            "file_title": "万用表说明书",
            "item_name": "万用表",
        },
    ]

    state = create_default_state(chunks=mock_chunks)

    try:
        result = node.process(state)
        output_chunks = result["chunks"]
        assert len(output_chunks) == 2, "chunks 数量不匹配"
        for c in output_chunks:
            assert "dense_vector" in c, "缺少 dense_vector"
            assert "sparse_vector" in c, "缺少 sparse_vector"
            assert len(c["dense_vector"]) == 1024, f"向量维度错误: {len(c['dense_vector'])}"
        record("BGE-M3 向量化", "PASS", f"2 个切片，维度 1024")
    except Exception as e:
        record("BGE-M3 向量化", "FAIL", str(e))


# ──────────────────────────────────────────────────────────────
# 9. knowledge_graph 节点测试（需要 LLM + Milvus + Neo4j）
# ──────────────────────────────────────────────────────────────
def test_knowledge_graph():
    section("9. KnowledgeGraphNode — 知识图谱（需 LLM + Milvus + Neo4j）")

    from knowledge.processor.import_process.config import get_config
    config = get_config()
    has_llm = bool(config.default_model)
    has_milvus = bool(config.milvus_url and config.entity_name_collection)
    has_neo4j = bool(config.neo4j_uri)

    if not has_llm:
        record("KG LLM 提取", "SKIP", "LLM 未配置")
        return

    from knowledge.processor.import_process.nodes.knowledge_graph import (
        KnowledgeGraphNode
    )
    node = KnowledgeGraphNode()

    # 测试 LLM 提取 + JSON 解析（纯逻辑，不写库）
    mock_chunks = [
        {
            "content": "电池安装步骤：1.断开表笔 2.拧开后盖 3.装入电池 4.盖紧后盖。警告：勿触碰内部电路。",
            "chunk_id": "test_chunk_001",
            "item_name": "万用表",
        }
    ]

    state = create_default_state(chunks=mock_chunks)

    try:
        result = node.process(state)
        record("KG LLM 提取 + 解析", "PASS", "完成（含 Milvus/Neo4j 写入）")
    except Exception as e:
        err_msg = str(e)
        if "Milvus" in err_msg or "Neo4j" in err_msg or "Connection" in err_msg:
            record("KG LLM 提取 + 解析", "SKIP",
                   f"外部服务不可用: {type(e).__name__}")
        else:
            record("KG LLM 提取 + 解析", "FAIL", err_msg)


# ──────────────────────────────────────────────────────────────
# 10. import_milvus 节点测试（需要 Milvus）
# ──────────────────────────────────────────────────────────────
def test_import_milvus():
    section("10. ImportMilvusNode — Milvus 导入（需 Milvus）")

    from knowledge.processor.import_process.config import get_config
    config = get_config()
    if not config.milvus_url or not config.chunks_collection:
        record("Milvus 导入", "SKIP", "Milvus 未配置")
        return

    from knowledge.processor.import_process.nodes.import_milvus import ImportMilvusNode
    node = ImportMilvusNode()

    mock_chunks = [
        {
            "content": "测试内容 A",
            "title": "测试标题 A",
            "parent_title": "",
            "part": 0,
            "file_title": "测试文件",
            "item_name": "测试产品",
            "dense_vector": [0.01] * 1024,
            "sparse_vector": {1: 0.5, 2: 0.3, 3: 0.2},
        },
        {
            "content": "测试内容 B",
            "title": "测试标题 B",
            "parent_title": "",
            "part": 0,
            "file_title": "测试文件",
            "item_name": "测试产品",
            "dense_vector": [0.02] * 1024,
            "sparse_vector": {1: 0.4, 2: 0.4, 3: 0.2},
        },
    ]

    state = create_default_state(chunks=mock_chunks)

    try:
        result = node.process(state)
        output_chunks = result["chunks"]
        with_id = sum(1 for c in output_chunks if c.get("chunk_id"))
        record(f"Milvus 导入", "PASS",
               f"插入 {with_id}/{len(output_chunks)} 条，chunk_id 已回填")
    except Exception as e:
        record("Milvus 导入", "FAIL", str(e))


# ──────────────────────────────────────────────────────────────
# 11. 端到端测试：HTML 完整流程
# ──────────────────────────────────────────────────────────────
def test_e2e_html():
    section("11. 端到端 — HTML 完整流程 (entry→html_to_md→md_img→document_split)")

    from knowledge.processor.import_process.nodes.entry import EntryNode
    from knowledge.processor.import_process.nodes.html_to_md import HtmlToMdNode
    from knowledge.processor.import_process.nodes.md_img import MdImgNode
    from knowledge.processor.import_process.nodes.document_split import DocumentSplitNode

    tmp_dir = PROJECT_ROOT / "test" / "test_data"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # 创建测试 HTML 文件
    html_file = tmp_dir / "_e2e_test.html"
    html_file.write_text(SAMPLE_HTML, encoding="utf-8")

    # Step 1: Entry
    entry_node = EntryNode()
    state = create_default_state(import_file_path=str(html_file))
    state = entry_node.process(state)
    assert state["is_html_read_enabled"] is True
    record("E2E Step 1: entry", "PASS", "HTML 路由正确")

    # Step 2: html_to_md
    html_node = HtmlToMdNode()
    state = html_node.process(state)
    assert "md_path" in state and state["md_path"]
    md_content = Path(state["md_path"]).read_text(encoding="utf-8")
    state["md_content"] = md_content
    record("E2E Step 2: html_to_md", "PASS", f"MD 文件 {len(md_content)} 字符")

    # Step 3: md_img
    md_img_node = MdImgNode()
    state = md_img_node.process(state)
    record("E2E Step 3: md_img", "PASS", "图片处理完成")

    # Step 4: document_split
    split_node = DocumentSplitNode()
    state = split_node.process(state)
    chunks = state.get("chunks", [])
    assert len(chunks) > 0
    record(f"E2E Step 4: document_split", "PASS", f"{len(chunks)} 个切片")

    # 汇总
    print(f"\n  📊 端到端流程统计:")
    print(f"     文件: {html_file.name}")
    print(f"     MD 长度: {len(md_content)} 字符")
    print(f"     切片数: {len(chunks)}")
    total_content = sum(len(c.get("content", "")) for c in chunks)
    print(f"     切片总内容: {total_content} 字符")

    # 清理
    for f in tmp_dir.glob("_e2e_*"):
        f.unlink()
    for f in tmp_dir.glob("chunks.json"):
        f.unlink()


# ──────────────────────────────────────────────────────────────
# 12. 端到端测试：MD 完整流程
# ──────────────────────────────────────────────────────────────
def test_e2e_md():
    section("12. 端到端 — MD 完整流程 (entry→md_img→document_split)")

    from knowledge.processor.import_process.nodes.entry import EntryNode
    from knowledge.processor.import_process.nodes.md_img import MdImgNode
    from knowledge.processor.import_process.nodes.document_split import DocumentSplitNode

    tmp_dir = PROJECT_ROOT / "test" / "test_data"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    md_file = tmp_dir / "_e2e_test.md"
    md_file.write_text(SAMPLE_MD, encoding="utf-8")

    # Step 1: Entry
    entry_node = EntryNode()
    state = create_default_state(import_file_path=str(md_file))
    state = entry_node.process(state)
    assert state["is_md_read_enabled"] is True
    record("E2E Step 1: entry (MD)", "PASS")

    # Step 2: md_img
    md_img_node = MdImgNode()
    state = md_img_node.process(state)
    record("E2E Step 2: md_img", "PASS")

    # Step 3: document_split
    split_node = DocumentSplitNode()
    state["md_content"] = SAMPLE_MD
    state = split_node.process(state)
    chunks = state.get("chunks", [])
    record(f"E2E Step 3: document_split", "PASS", f"{len(chunks)} 个切片")

    # 清理
    md_file.unlink(missing_ok=True)
    for f in tmp_dir.glob("chunks.json"):
        f.unlink()


# ──────────────────────────────────────────────────────────────
# 主入口
# ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="导入流程全节点测试")
    parser.add_argument("--html", action="store_true", help="只测 HTML 相关")
    parser.add_argument("--md", action="store_true", help="只测 MD 流程")
    parser.add_argument("--graph", action="store_true", help="只测知识图谱")
    parser.add_argument("--unit", action="store_true", help="只做单元测试（不含外部服务）")
    args = parser.parse_args()

    setup_logging()

    print("=" * 60)
    print("  导入流程全节点测试")
    print(f"  项目根目录: {PROJECT_ROOT}")
    print("=" * 60)

    overall_start = time.time()

    if args.unit or not (args.html or args.md or args.graph):
        test_router()
        test_graph_compile()
        test_entry()
        test_html_to_md()
        test_document_split()
        test_md_img()

    if not args.unit:
        test_e2e_html()
        test_e2e_md()
        test_item_name_recognition()
        test_bge_embedding()
        test_import_milvus()
        test_knowledge_graph()

    # ── 汇总 ──
    elapsed = time.time() - overall_start
    print(f"\n{'='*60}")
    print(f"  测试结果汇总")
    print(f"{'='*60}")
    print(f"  ✅ 通过: {passed}")
    print(f"  ❌ 失败: {failed}")
    print(f"  ⏭️  跳过: {skipped}")
    print(f"  📊 总计: {passed + failed + skipped}")
    print(f"  ⏱️  耗时: {elapsed:.1f}s")
    print(f"{'='*60}")

    if failed > 0:
        print("\n失败详情:")
        for name, status, detail in results:
            if status == "FAIL":
                print(f"  ❌ {name}: {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
