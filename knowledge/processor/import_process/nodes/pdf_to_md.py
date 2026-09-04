# knowledge/processor/import_process/nodes/pdf_to_md.py

"""
PDF 转 Markdown 节点

使用 MinerU 云端 API 将 PDF 文档转换为 Markdown 格式。
流程：请求上传地址 → 上传文件 → 轮询任务状态 → 下载结果 ZIP → 解压获取 Markdown
"""

import json
import os
import time
import zipfile
import logging
import requests
from pathlib import Path
from dotenv import load_dotenv

from knowledge.processor.import_process.base import BaseNode, setup_logging
from knowledge.processor.import_process.state import ImportGraphState
from knowledge.processor.import_process.exceptions import PdfConversionError, FileProcessingError

load_dotenv(Path(__file__).resolve().parent.parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

MINERU_KEY = os.getenv("MINERU_KEY", "")
MINERU_BATCH_URL = "https://mineru.net/api/v4/file-urls/batch"
MINERU_BATCH_RESULT_URL = "https://mineru.net/api/v4/extract-results/batch"
MINERU_MODEL_VERSION = os.getenv("MINERU_MODEL_VERSION", "vlm")
MINERU_MAX_RETRIES = int(os.getenv("MINERU_MAX_RETRIES", "120"))
MINERU_POLL_INTERVAL = int(os.getenv("MINERU_POLL_INTERVAL", "5"))


class PdfToMdNode(BaseNode):
    """
    PDF 转 Markdown 节点

    通过 MinerU 云端 API 将 PDF 转换为 Markdown，
    支持进度日志输出。
    """

    name = "pdf_to_md"

    def process(self, state: ImportGraphState) -> ImportGraphState:
        """
        执行 PDF 转换

        1. 验证 PDF 路径
        2. 上传文件到 MinerU 云端
        3. 轮询转换状态
        4. 下载并解压结果

        Args:
            state: 图状态

        Returns:
            更新后的状态（包含 md_path）
        """
        # Step 1: 验证路径
        pdf_path_obj, output_dir_obj = self._validate_paths(state)

        # Step 2: 云端转换
        self.log_step("step_2", "执行 MinerU 云端转换")
        md_path = self._cloud_convert(pdf_path_obj, output_dir_obj)

        # Step 3: 返回结果
        state["md_path"] = md_path
        self.log_step("step_3", f"输出路径: {md_path}")

        return state

    def _validate_paths(self, state: ImportGraphState) -> tuple:
        """
        验证 PDF 路径和输出目录

        Args:
            state: 图状态

        Returns:
            (pdf_path_obj, output_dir_obj) 元组

        Raises:
            FileProcessingError: 路径无效时抛出
        """
        self.log_step("step_1", "验证路径")

        pdf_path = state.get("pdf_path", "")
        if not pdf_path:
            raise FileProcessingError("pdf_path 为空", node_name=self.name)

        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            raise FileProcessingError(
                f"PDF 文件不存在: {pdf_path}",
                node_name=self.name
            )

        output_dir = state.get("file_dir", "")
        if not output_dir:
            # 使用 .env 中配置的临时目录，避免权限问题
            from knowledge.core.paths import get_temp_root
            output_dir = get_temp_root()

        output_dir_obj = Path(output_dir)
        self.logger.info(f"处理 PDF: {pdf_path_obj.name}")

        return pdf_path_obj, output_dir_obj

    def _cloud_convert(self, pdf_path_obj: Path, output_dir_obj: Path) -> str:
        """
        MinerU 云端转换全流程

        Args:
            pdf_path_obj: PDF 文件路径
            output_dir_obj: 输出目录

        Returns:
            Markdown 文件路径
        """
        start_ts = time.time()

        # 1. 请求上传地址
        batch_id, upload_url = self._request_upload_url(pdf_path_obj.name)
        self.logger.info(f"获取上传地址成功, batch_id={batch_id}")

        # 2. 上传文件
        self._upload_file(pdf_path_obj, upload_url)
        self.logger.info("文件上传完成，等待云端转换")

        # 3. 轮询任务状态
        zip_url = self._poll_task_result(batch_id)
        self.logger.info("云端转换完成，开始下载结果")

        # 4. 下载并解压
        md_path = self._download_and_extract(zip_url, output_dir_obj, pdf_path_obj.stem)

        elapsed = time.time() - start_ts
        self.logger.info(f"转换完成，耗时: {elapsed:.1f} 秒")

        return md_path

    def _request_upload_url(self, filename: str) -> tuple:
        """请求文件上传预签名 URL"""
        resp = requests.post(
            MINERU_BATCH_URL,
            headers=self._get_headers(),
            json={
                "files": [{"name": filename}],
                "model_version": MINERU_MODEL_VERSION,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise PdfConversionError(
                f"请求上传地址失败: {data.get('msg')}",
                node_name=self.name
            )

        batch_id = data["data"]["batch_id"]
        file_urls = data["data"]["file_urls"]
        return batch_id, file_urls[0]

    def _upload_file(self, pdf_path_obj: Path, upload_url: str):
        """上传文件到预签名 URL"""
        with open(pdf_path_obj, "rb") as f:
            resp = requests.put(upload_url, data=f, timeout=300)
        if resp.status_code != 200:
            raise PdfConversionError(
                f"文件上传失败: HTTP {resp.status_code}",
                node_name=self.name
            )

    def _poll_task_result(self, batch_id: str) -> str:
        """轮询任务结果，返回 ZIP 下载 URL"""
        url = f"{MINERU_BATCH_RESULT_URL}/{batch_id}"

        for i in range(MINERU_MAX_RETRIES):
            resp = requests.get(url, headers=self._get_headers(), timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                raise PdfConversionError(
                    f"查询任务状态失败: {data.get('msg')}",
                    node_name=self.name
                )

            results = data.get("data", {}).get("extract_result", [])
            if not results:
                self.logger.info(f"等待任务创建... ({i + 1}/{MINERU_MAX_RETRIES})")
                time.sleep(MINERU_POLL_INTERVAL)
                continue

            result = results[0]
            state = result.get("state", "")

            if state == "done":
                return result["full_zip_url"]
            elif state == "failed":
                err = result.get("err_msg", "未知错误")
                raise PdfConversionError(
                    f"MinerU 转换失败: {err}",
                    node_name=self.name
                )
            else:
                progress = result.get("extract_progress", {})
                extracted = progress.get("extracted_pages", "?")
                total = progress.get("total_pages", "?")
                self.logger.info(
                    f"转换中... 状态={state}, 页数={extracted}/{total} "
                    f"({i + 1}/{MINERU_MAX_RETRIES})"
                )
                time.sleep(MINERU_POLL_INTERVAL)

        raise PdfConversionError(
            f"MinerU 转换超时（{MINERU_MAX_RETRIES * MINERU_POLL_INTERVAL}秒）",
            node_name=self.name
        )

    def _download_and_extract(self, zip_url: str, output_dir: Path, file_stem: str) -> str:
        """下载 ZIP 并解压，返回 Markdown 文件路径"""
        resp = requests.get(zip_url, timeout=120)
        resp.raise_for_status()

        zip_path = output_dir / f"{file_stem}.zip"
        with open(zip_path, "wb") as f:
            f.write(resp.content)

        extract_dir = output_dir / file_stem
        extract_dir.mkdir(parents=True, exist_ok=True)

        # 只解压 .md 和 images/ 下的文件，跳过 PDF 等大文件
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                name = info.filename
                if name.endswith(".md") or name.startswith("images/"):
                    zf.extract(info, extract_dir)

        # 优先查找 full.md，其次任意 .md 文件
        for md_file in extract_dir.rglob("*.md"):
            return str(md_file)

        raise PdfConversionError(
            f"ZIP 中未找到 Markdown 文件: {zip_path}",
            node_name=self.name
        )

    @staticmethod
    def _get_headers():
        """构建请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MINERU_KEY}",
        }


# ================================================================== #
#                        兼容 & 测试                                  #
# ================================================================== #

node_pdf_to_md = PdfToMdNode()


if __name__ == '__main__':
    """
    PDF 转 Markdown 节点测试
    """
    setup_logging()

    print("=" * 60)
    print("PDF to MD 节点测试（MinerU 云端 API）")
    print("=" * 60)

    pdf_to_md_node = PdfToMdNode()

    # 请修改为实际存在的 PDF 文件路径
    test_pdf_path = r"E:\work_space\掌柜智库\002\knowledge\test\test_data\大模型FastApi.pdf"
    test_output_dir = r"E:\work_space\掌柜智库\002\knowledge\test\test_data\output"

    if not Path(test_pdf_path).exists():
        print(f"警告: 测试文件不存在: {test_pdf_path}")
        print("请修改 test_pdf_path 为有效的 PDF 文件路径")
    else:
        state = {
            "pdf_path": test_pdf_path,
            "file_dir": test_output_dir
        }

        try:
            result = pdf_to_md_node.process(state)
            print("转换成功!")
            print(json.dumps(result, indent=4, ensure_ascii=False))

            md_path = Path(result["md_path"])
            if md_path.exists():
                print(f"\n输出文件已生成: {md_path}")
                print(f"文件大小: {md_path.stat().st_size} 字节")
            else:
                print(f"警告: 输出文件不存在: {md_path}")

        except PdfConversionError as e:
            print(f"转换失败: {e}")
        except FileProcessingError as e:
            print(f"文件处理错误: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
