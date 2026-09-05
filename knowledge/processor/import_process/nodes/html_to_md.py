# knowledge/processor/import_process/nodes/html_to_md.py

"""
HTML 转 Markdown 节点

将 HTML 文件解析为 Markdown 格式，保留标题、段落、列表、表格等结构信息。
使用 BeautifulSoup + html2text 进行结构化转换。
"""

import os
import logging
from pathlib import Path

from knowledge.processor.import_process.base import BaseNode
from knowledge.processor.import_process.state import ImportGraphState
from knowledge.processor.import_process.exceptions import FileProcessingError
from knowledge.tools.html_utils import html_file_to_markdown_file

logger = logging.getLogger(__name__)


class HtmlToMdNode(BaseNode):
    """
    HTML 转 Markdown 节点

    读取 HTML 文件，清理无关标签（脚本、样式、导航等），
    将结构化内容转换为 Markdown，输出到同目录下的同名 .md 文件。
    """

    name = "html_to_md"

    def process(self, state: ImportGraphState) -> ImportGraphState:
        """
        执行 HTML 转换

        1. 验证 HTML 路径
        2. 调用 html_utils 转换
        3. 将输出路径写入 state

        Args:
            state: 图状态

        Returns:
            更新后的状态（包含 md_path）
        """
        # Step 1: 验证路径
        html_path_obj, output_dir_obj = self._validate_paths(state)

        # Step 2: 执行转换
        self.log_step("step_2", "执行 HTML → Markdown 转换")
        md_path = self._convert(html_path_obj, output_dir_obj)

        # Step 3: 写入状态
        state["md_path"] = md_path
        self.log_step("step_3", f"输出路径: {md_path}")

        return state

    def _validate_paths(self, state: ImportGraphState) -> tuple:
        """
        验证 HTML 路径和输出目录

        Args:
            state: 图状态

        Returns:
            (html_path_obj, output_dir_obj) 元组

        Raises:
            FileProcessingError: 路径无效时抛出
        """
        self.log_step("step_1", "验证路径")

        html_path = state.get("html_path", "")
        if not html_path:
            raise FileProcessingError("html_path 为空", node_name=self.name)

        html_path_obj = Path(html_path)
        if not html_path_obj.exists():
            raise FileProcessingError(
                f"HTML 文件不存在: {html_path}",
                node_name=self.name
            )

        output_dir = state.get("file_dir", "")
        if not output_dir:
            from knowledge.core.paths import get_temp_root
            output_dir = get_temp_root()

        output_dir_obj = Path(output_dir)
        self.logger.info(f"处理 HTML: {html_path_obj.name}")

        return html_path_obj, output_dir_obj

    def _convert(self, html_path_obj: Path, output_dir_obj: Path) -> str:
        """
        执行 HTML → Markdown 转换

        Args:
            html_path_obj: HTML 文件路径
            output_dir_obj: 输出目录

        Returns:
            Markdown 文件路径
        """
        import time
        start_ts = time.time()

        # 确定输出路径：放在 file_dir 下，使用 stem + "_converted" 命名
        output_path = output_dir_obj / f"{html_path_obj.stem}_converted.md"

        self.logger.info(f"转换 HTML → Markdown: {html_path_obj.name} → {output_path.name}")
        md_path = html_file_to_markdown_file(str(html_path_obj), str(output_path))

        elapsed = time.time() - start_ts
        self.logger.info(f"转换完成，耗时: {elapsed:.1f} 秒")

        return md_path


# ================================================================== #
#                        兼容 & 测试                                  #
# ================================================================== #

node_html_to_md = HtmlToMdNode()


if __name__ == '__main__':
    """
    HTML 转 Markdown 节点测试
    """
    from knowledge.processor.import_process.base import setup_logging

    setup_logging()

    print("=" * 60)
    print("HTML to MD 节点测试")
    print("=" * 60)

    html_to_md_node = HtmlToMdNode()

    # 查找测试目录下是否有 HTML 文件
    test_html = r"E:\work_space\掌柜智库\002\knowledge\test\test_data\test.html"
    test_output = r"E:\work_space\掌柜智库\002\knowledge\test\test_data\output"

    if not Path(test_html).exists():
        print(f"未找到测试文件: {test_html}")
        print("请放置一个 .html 文件到 test/test_data/ 目录下")
    else:
        state = {
            "html_path": test_html,
            "file_dir": test_output,
        }

        try:
            result = html_to_md_node.process(state)
            print("转换成功!")
            md_path = Path(result["md_path"])
            print(f"输出文件: {md_path}")
            print(f"文件大小: {md_path.stat().st_size} 字节")
            print("\n--- Markdown 内容预览（前 500 字符）---")
            print(md_path.read_text(encoding="utf-8")[:500])
        except FileProcessingError as e:
            print(f"转换失败: {e}")
