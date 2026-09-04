"""查询请求/响应数据模型"""

from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str = Field(..., description="查询内容")
    session_id: Optional[str] = Field(None, description="会话ID")
    is_stream: bool = Field(False, description="是否流式返回")


class QueryResponse(BaseModel):
    """查询响应模型（非流式）"""
    session_id: str = Field(..., description="会话ID")
    answer: str = Field("", description="回答内容")


class QuerySubmitResponse(BaseModel):
    """流式查询提交响应"""
    message: str = Field("Query submitted", description="提示信息")
    session_id: str = Field(..., description="会话ID")


class HistoryItem(BaseModel):
    """历史对话条目"""
    role: str = Field("", description="角色")
    text: str = Field("", description="内容")
    rewritten_query: str = Field("", description="改写查询")
    item_names: list = Field(default_factory=list, description="商品名称")
    ts: Optional[float] = Field(None, description="时间戳")


class HistoryResponse(BaseModel):
    """历史对话响应"""
    session_id: str = Field(..., description="会话ID")
    items: list = Field(default_factory=list, description="对话列表")
