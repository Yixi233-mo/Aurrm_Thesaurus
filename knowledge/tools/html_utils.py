# knowledge/tools/html_utils.py

"""
HTML 解析工具函数

提供 HTML 文件到纯文本/Markdown 的转换能力，
基于 BeautifulSoup 清理 + html2text 结构化提取。
"""

import re
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, Comment, Doctype

try:
    import html2text
    _HAS_HTML2TEXT = True
except ImportError:
    _HAS_HTML2TEXT = False


# 需要移除的无意义标签
_TAGS_REMOVE = frozenset([
    "script", "style", "noscript", "nav", "header", "footer",
    "aside", "iframe", "svg", "canvas", "form", "button",
    "input", "select", "textarea",
])

# 需要移除的 class/id 关键词（广告/导航/无关内容）
_CLASS_ID_PATTERN = re.compile(
    r"(nav|menu|sidebar|footer|header|advert|cookie|banner|popup|modal)"
    r"(?:[-_]?\w+)*",
    re.IGNORECASE,
)


def _should_remove_tag(tag) -> bool:
    """
    判断标签是否应被移除

    检查条件：
    1. 标签名在移除列表中
    2. class 或 id 包含导航/广告等关键词
    """
    if tag.name in _TAGS_REMOVE:
        return True

    # 检查 class 和 id
    class_str = " ".join(tag.get("class", []))
    id_str = tag.get("id", "")
    combined = f"{class_str} {id_str}"

    if _CLASS_ID_PATTERN.search(combined):
        return True

    return False


def clean_html(html_content: str) -> BeautifulSoup:
    """
    清理 HTML 内容：移除无用标签和注释

    Args:
        html_content: 原始 HTML 字符串

    Returns:
        清理后的 BeautifulSoup 对象
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 移除注释和 DOCTYPE
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    for doctype in soup.find_all(string=lambda text: isinstance(text, Doctype)):
        doctype.extract()

    # 移除无用标签（含其子内容）
    for tag in soup.find_all(_should_remove_tag):
        tag.decompose()

    # 移除所有标签的 style 和 onclick 等内联属性
    for tag in soup.find_all(True):
        # 保留 lang、dir 等语义属性，移除行为和样式属性
        attrs_to_remove = []
        for attr in tag.attrs:
            if attr in ("style", "onclick", "onload", "onmouseover",
                        "onfocus", "onblur", "onsubmit"):
                attrs_to_remove.append(attr)
        for attr in attrs_to_remove:
            del tag[attr]

    return soup


def html_to_markdown(html_content: str, base_url: str = "") -> str:
    """
    将 HTML 内容转换为 Markdown

    优先使用 html2text 库进行结构化转换，
    否则回退到 BeautifulSoup 手动提取文本。

    Args:
        html_content: 原始 HTML 字符串
        base_url: 基础 URL（用于 html2text 解析相对链接）

    Returns:
        Markdown 格式文本
    """
    soup = clean_html(html_content)

    if _HAS_HTML2TEXT:
        try:
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.body_width = 0  # 不自动换行，保留原始结构
            h.unicode_snob = True
            h.skip_internal_links = False
            if base_url:
                h.baseurl = base_url

            # 从清理后的 soup 重新序列化
            cleaned_html = str(soup)
            return h.handle(cleaned_html)
        except Exception:
            pass  # 回退到手动提取

    # 回退方案：手动提取结构化文本
    return _manual_extract(soup)


def _manual_extract(soup: BeautifulSoup) -> str:
    """
    手动提取 BeautifulSoup 中的结构化文本

    保留标题层级、段落、列表、表格等结构信息。
    """
    parts = []

    def process_tag(tag, level=0):
        """递归处理标签"""
        tag_name = tag.name
        if tag_name is None:
            return

        # 文本节点
        if tag_name == "br":
            parts.append("\n")
            return

        text = tag.get_text(strip=True)
        if not text and tag_name not in ("img",):
            return

        # 标题层级
        if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            heading_level = int(tag_name[1])
            parts.append(f"\n{'#' * heading_level} {text}\n")
            return

        # 段落
        if tag_name == "p":
            parts.append(f"\n{text}\n")
            return

        # 链接
        if tag_name == "a":
            href = tag.get("href", "")
            if href:
                parts.append(f"[{text}]({href})")
            else:
                parts.append(text)
            return

        # 图片
        if tag_name == "img":
            alt = tag.get("alt", "")
            src = tag.get("src", "")
            if src:
                parts.append(f"![{alt}]({src})")
            elif alt:
                parts.append(f"[图片: {alt}]")
            return

        # 列表
        if tag_name in ("ul", "ol"):
            is_ordered = tag_name == "ol"
            for idx, li in enumerate(tag.find_all("li", recursive=False)):
                li_text = li.get_text(strip=True)
                prefix = f"{idx + 1}." if is_ordered else "-"
                parts.append(f"{prefix} {li_text}\n")
            return

        # 表格
        if tag_name == "table":
            parts.append("\n")
            rows = tag.find_all("tr")
            for i, row in enumerate(rows):
                cells = row.find_all(["td", "th"])
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                parts.append("| " + " | ".join(cell_texts) + " |")
                if i == 0:
                    parts.append("| " + " | ".join(["---"] * len(cells)) + " |")
            parts.append("\n")
            return

        # 代码块
        if tag_name in ("pre", "code"):
            parts.append(f"\n```\n{text}\n```\n")
            return

        # 块级元素前后加换行
        if tag_name in ("div", "section", "article", "blockquote",
                         "hr", "main", "figure"):
            parts.append("\n")

        # 递归处理子元素
        for child in tag.children:
            if hasattr(child, "name"):
                process_tag(child, level + 1)
            elif isinstance(child, str) and child.strip():
                parts.append(child.strip())

    # 从 body 开始处理，若没有 body 则从根开始
    body = soup.find("body") or soup
    for child in body.children:
        if hasattr(child, "name") and child.name:
            process_tag(child)
        elif isinstance(child, str) and child.strip():
            parts.append(child.strip())

    result = "".join(parts)
    # 清理多余空行
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def html_file_to_markdown_file(
    html_path: str,
    output_path: Optional[str] = None,
) -> str:
    """
    将 HTML 文件转换为 Markdown 文件

    Args:
        html_path: 输入 HTML 文件路径
        output_path: 输出 Markdown 文件路径（可选，默认在同目录下生成同名 .md 文件）

    Returns:
        输出 Markdown 文件的绝对路径

    Raises:
        FileProcessingError: 文件不存在或读写失败时抛出（调用方处理）
    """
    html_path_obj = Path(html_path)
    if not html_path_obj.exists():
        raise FileNotFoundError(f"HTML 文件不存在: {html_path}")

    # 读取 HTML 文件
    try:
        with open(html_path_obj, "r", encoding="utf-8") as f:
            html_content = f.read()
    except UnicodeDecodeError:
        # 回退到 GBK 编码（常见于中文 Windows 系统生成的 HTML）
        with open(html_path_obj, "r", encoding="gbk") as f:
            html_content = f.read()

    # 转换为 Markdown
    md_content = html_to_markdown(html_content)

    # 确定输出路径
    if output_path is None:
        output_path_obj = html_path_obj.with_suffix(".md")
    else:
        output_path_obj = Path(output_path)

    # 写入 Markdown 文件
    try:
        with open(output_path_obj, "w", encoding="utf-8") as f:
            f.write(md_content)
    except IOError as e:
        raise IOError(f"写入 Markdown 文件失败 {output_path_obj}: {e}")

    return str(output_path_obj.resolve())
