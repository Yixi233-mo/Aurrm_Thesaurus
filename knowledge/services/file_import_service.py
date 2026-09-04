"""文件导入服务"""

import os
import uuid
import logging
from datetime import datetime
from typing import List, Tuple

from knowledge.services.task_service import TaskService
from knowledge.tools.task_utils import TASK_STATUS_PROCESSING, TASK_STATUS_COMPLETED, TASK_STATUS_FAILED

logger = logging.getLogger(__name__)

_file_import_service = None


def get_file_import_service():
    global _file_import_service
    if _file_import_service is None:
        _file_import_service = FileImportService()
    return _file_import_service


class FileImportService:
    """文件导入服务类"""

    def __init__(self):
        from knowledge.core.paths import get_temp_root
        self.base_dir = get_temp_root()

    def get_date_dir(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        date_dir = os.path.join(self.base_dir, date_str)
        os.makedirs(date_dir, exist_ok=True)
        return date_dir

    def process_files(self, files) -> Tuple[List[str], str]:
        """处理文件上传，保存到本地并上传 MinIO

        Args:
            files: 文件数据列表，每个元素为 {"filename": str, "content": bytes}
        """
        from knowledge.tools.minio_utils import get_minio_client
        from knowledge.tools.minio_utils import MINIO_BUCKET_NAME

        date_dir = self.get_date_dir()
        task_ids = []
        minio_client = get_minio_client()

        for file_data in files:
            filename = file_data["filename"]
            content = file_data["content"]

            task_id = str(uuid.uuid4())
            task_ids.append(task_id)

            TaskService.create_task_node(task_id, "upload_file")

            file_dir = os.path.join(date_dir, task_id)
            os.makedirs(file_dir, exist_ok=True)

            file_path = os.path.join(file_dir, filename)
            with open(file_path, "wb") as f:
                f.write(content)

            if minio_client:
                try:
                    minio_client.fput_object(
                        MINIO_BUCKET_NAME,
                        f"{task_id}/{filename}",
                        file_path,
                    )
                except Exception as e:
                    logger.warning(f"MinIO 上传失败: {e}")

            TaskService.complete_task_node(task_id, "upload_file")

        return task_ids, date_dir

    def run_import_task(self, task_id: str, file_dir: str, import_file_path: str):
        """运行导入任务"""
        from knowledge.processor.import_process.main_graph import kb_import_app
        from knowledge.processor.import_process.state import create_default_state
        from knowledge.processor.import_process.base import setup_logging

        setup_logging()

        try:
            TaskService.update_status(task_id, TASK_STATUS_PROCESSING)

            initial_state = create_default_state(
                task_id=task_id,
                file_dir=file_dir,
                import_file_path=import_file_path,
            )

            for event in kb_import_app.stream(initial_state):
                for key, value in event.items():
                    if key != "__end__":
                        TaskService.complete_task_node(task_id, key)

            TaskService.update_status(task_id, TASK_STATUS_COMPLETED)

        except Exception as e:
            logger.error(f"导入任务失败: {e}")
            TaskService.update_status(task_id, TASK_STATUS_FAILED)
