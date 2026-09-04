"""
knowledge/tools/
└──task_utils.py
"""

from typing import Any, Dict, List
from collections import defaultdict

# 只要访问不存在的 key，自动帮你初始化为 []
_tasks_running_list: Dict[str, List[str]] = defaultdict(list)
_tasks_done_list: Dict[str, List[str]] = defaultdict(list)

# 只要访问不存在的 key，自动帮你初始化为 {}
_tasks_result: Dict[str, Dict[str, str]] = defaultdict(dict)

_tasks_status: Dict[str, str] = {}
_tasks_sources: Dict[str, List[Dict[str, Any]]] = {}

TASK_STATUS_PROCESSING = "processing"  # 任务处理中
TASK_STATUS_COMPLETED = "completed"  # 任务完成
TASK_STATUS_FAILED = "failed"  # 任务失败

_NODE_NAME_TO_CN: Dict[str, str] = {
    "upload_file": "上传文件",
    "entry": "检查文件",
    "pdf_to_md": "PDF转Markdown",
    "md_img": "Markdown图片处理",
    "document_split": "文档切分",
    "item_name_recognition": "主体名称识别",
    "bge_embedding": "向量生成",
    "import_milvus": "导入向量数据库",
    "knowledge_graph": "导入知识图谱",
    "__end__": "处理完成",

    # --- Query 流程节点 ---
    "item_name_confirm": "确认问题产品",
    "answer_output": "生成答案",
    "rerank": "重排序",
    "rrf": "倒排融合",
    "web_search_mcp": "网络搜索",
    "search_embedding": "切片搜索",
    "search_embedding_hyde": "切片搜索(假设性文档)",
    "query_kg": "查询知识图谱"

}


def _to_cn(node_name: str) -> str:
    return _NODE_NAME_TO_CN.get(node_name, node_name)


def task_push_queue(task_id: str):
    """推送任务进度到 SSE 队列"""
    try:
        from knowledge.tools.sse_utils import push_sse_event, SSEEvent
        push_sse_event(task_id, SSEEvent.PROGRESS, {
            "status": get_task_status(task_id),
            "done_list": get_done_task_list(task_id),
            "running_list": get_running_task_list(task_id),
        })
    except Exception:
        pass


def add_running_task(task_id: str, node_name: str, push_queue: bool = False) -> None:
    running = _tasks_running_list[task_id]
    if node_name not in running:
        running.append(node_name)
    if push_queue:
        task_push_queue(task_id)


def add_done_task(task_id: str, node_name: str, push_queue: bool = False) -> None:
    if node_name in _tasks_running_list[task_id]:
        _tasks_running_list[task_id].remove(node_name)
    done = _tasks_done_list[task_id]
    if node_name not in done:
        done.append(node_name)
    if push_queue:
        task_push_queue(task_id)


def get_running_task_list(task_id: str) -> List[str]:
    # 1. 获取指定任务运行中的节点列表，并通过列表推导式统一转换为中文展示名返回
    return [_to_cn(n) for n in _tasks_running_list.get(task_id, [])]


def get_done_task_list(task_id: str) -> List[str]:
    # 1. 获取指定任务已完成的节点列表，并通过列表推导式统一转换为中文展示名返回
    return [_to_cn(n) for n in _tasks_done_list.get(task_id, [])]


def get_task_status(task_id: str) -> str:
    """
    根据任务ID 获取任务状态
    :param task_id:
    :return:
    """
    # 1. 安全获取指定任务的总体运行状态，若不存在则返回空字符串
    return _tasks_status.get(task_id, "")


def update_task_status(task_id: str, status_name: str, push_queue: bool = False) -> None:
    _tasks_status[task_id] = status_name
    if push_queue:
        task_push_queue(task_id)


def set_task_result(task_id: str, key: str, value: str) -> None:
    """
    存储任务结果字段（如 answer / error）。
    """
    _tasks_result[task_id][key] = value


def get_task_result(task_id: str, key: str, default: str = "") -> str:
    """
    获取任务结果字段（如 answer / error）。
    """
    return _tasks_result.get(task_id, {}).get(key, default)


def clear_task(task_id: str):
    # 1. 安全移除该任务的运行节点记录
    _tasks_running_list.pop(task_id, None)
    # 2. 安全移除该任务的已完成节点记录
    _tasks_done_list.pop(task_id, None)
    # 3. 安全移除该任务的总体状态记录
    _tasks_status.pop(task_id, None)
    # 4. 安全移除该任务的结果记录
    # _tasks_result.pop(task_id, None)
    # 5. 安全移除该任务的来源记录
    _tasks_sources.pop(task_id, None)


def set_task_sources(task_id: str, sources: List[Dict[str, Any]]) -> None:
    _tasks_sources[task_id] = sources


def get_task_sources(task_id: str) -> List[Dict[str, Any]]:
    return _tasks_sources.get(task_id, [])
