"""知识库查询 API 路由"""

import os
import sys
import uuid
import asyncio
import logging

# 确保项目根目录在 sys.path 中，便于 uvicorn 热重载子进程也能正确导入 knowledge 包
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from knowledge.schemas.query_schema import QueryRequest
from knowledge.tools.task_utils import (
    update_task_status,
    get_task_result,
    set_task_result,
    get_task_sources,
    set_task_sources,
    TASK_STATUS_PROCESSING,
    TASK_STATUS_COMPLETED,
)
from knowledge.tools.sse_utils import (
    create_sse_queue,
    sse_generator,
    push_sse_event,
    SSEEvent,
)
from knowledge.tools.mongo_history_utils import get_recent_messages, clear_history
from knowledge.core.paths import get_front_page_dir

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Query Service", description="知识库查询服务")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    page_dir = get_front_page_dir()
    dist_dir = os.path.join(page_dir, "dist")
    if os.path.exists(dist_dir):
        app.mount("/front", StaticFiles(directory=dist_dir, html=True), name="front")

    _register_routes(app)
    return app


def _register_routes(app: FastAPI):

    @app.get("/chat.html")
    async def chat_page():
        return RedirectResponse(url="/chat", status_code=301)

    @app.post("/query")
    async def query(request: QueryRequest, background_tasks: BackgroundTasks):
        user_query = request.query
        session_id = request.session_id or str(uuid.uuid4())
        is_stream = request.is_stream

        update_task_status(session_id, TASK_STATUS_PROCESSING, is_stream)

        if is_stream:
            # 在返回响应前创建 SSE 队列，消除前端连接时的竞态条件
            create_sse_queue(session_id)
            background_tasks.add_task(_run_query_graph, session_id, user_query, is_stream)
            await asyncio.sleep(0.1)
            return {"message": "Query submitted", "session_id": session_id}
        else:
            _run_query_graph(session_id, user_query, is_stream)
            answer = get_task_result(session_id, "answer", "")
            sources = get_task_sources(session_id)
            return {"session_id": session_id, "answer": answer, "sources": sources}

    @app.get("/stream/{session_id}")
    async def stream(session_id: str, request: Request):
        return StreamingResponse(
            sse_generator(session_id, request),
            media_type="text/event-stream",
        )

    @app.get("/history/{session_id}")
    async def history(session_id: str, limit: int = 50):
        records = get_recent_messages(session_id, limit=limit)
        items = [
            {
                "role": r.get("role", ""),
                "text": r.get("text", ""),
                "rewritten_query": r.get("rewritten_query", ""),
                "item_names": r.get("item_names", []),
                "ts": r.get("ts"),
            }
            for r in records
        ]
        return {"session_id": session_id, "items": items}

    @app.delete("/history/{session_id}")
    async def clear_chat_history(session_id: str):
        count = clear_history(session_id)
        return {"deleted_count": count}


def _run_query_graph(session_id: str, user_query: str, is_stream: bool):
    from knowledge.processor.query_process.main_graph import query_app

    default_state = {
        "original_query": user_query,
        "session_id": session_id,
        "is_stream": is_stream,
        "item_names": [],
        "history": [],
    }

    try:
        query_app.invoke(default_state)
    except Exception as e:
        logger.error(f"查询流程执行失败: {e}")
        error_msg = f"抱歉，处理时出现错误: {e}"
        set_task_result(session_id, "answer", error_msg)
        # 推送 FINAL 事件，避免前端 SSE 流永久悬挂
        push_sse_event(session_id, SSEEvent.FINAL, {"answer": error_msg, "sources": []})

    update_task_status(session_id, TASK_STATUS_COMPLETED, is_stream)


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
