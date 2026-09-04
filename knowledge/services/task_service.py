"""任务状态服务"""

from typing import Dict
from knowledge.tools.task_utils import (
    add_running_task,
    add_done_task,
    get_task_status,
    get_done_task_list,
    get_running_task_list,
    update_task_status,
    set_task_result,
    get_task_result,
    clear_task,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
)


class TaskService:
    """任务服务类"""

    @staticmethod
    def create_task_node(task_id: str, initial_node: str = "upload_file", push_queue: bool = False):
        add_running_task(task_id, initial_node, push_queue)

    @staticmethod
    def complete_task_node(task_id: str, node_name: str, push_queue: bool = False):
        add_done_task(task_id, node_name, push_queue)

    @staticmethod
    def update_status(task_id: str, status: str, push_queue: bool = False):
        update_task_status(task_id, status, push_queue)

    @staticmethod
    def set_result(task_id: str, key: str, value: str):
        set_task_result(task_id, key, value)

    @staticmethod
    def get_result(task_id: str, key: str, default: str = "") -> str:
        return get_task_result(task_id, key, default)

    @staticmethod
    def get_task_info(task_id: str) -> Dict:
        return {
            "status": get_task_status(task_id),
            "done_list": get_done_task_list(task_id),
            "running_list": get_running_task_list(task_id),
        }

    @staticmethod
    def clear(task_id: str):
        clear_task(task_id)
