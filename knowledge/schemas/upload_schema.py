"""文件上传数据模型"""

from typing import List
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """文件上传响应"""
    message: str = Field("Files uploaded successfully", description="提示信息")
    task_ids: List[str] = Field(default_factory=list, description="任务ID列表")
