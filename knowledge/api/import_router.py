"""知识库导入 API 路由"""

import os
import logging
from typing import List

from fastapi import FastAPI, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from knowledge.schemas.upload_schema import UploadResponse
from knowledge.schemas.task_schema import TaskStatusResponse
from knowledge.services.file_import_service import get_file_import_service
from knowledge.services.task_service import TaskService
from knowledge.core.paths import get_front_page_dir

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Import Service", description="知识库导入服务")

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

    @app.get("/import.html")
    async def import_page():
        return RedirectResponse(url="/import", status_code=301)

    @app.post("/upload", response_model=UploadResponse)
    async def upload_files(
        background_tasks: BackgroundTasks,
        files: List[UploadFile] = File(...),
    ):
        import traceback
        try:
            service = get_file_import_service()

            # 在 async 上下文中先读取文件内容，避免同步阻塞事件循环
            file_data = []
            for file in files:
                content = await file.read()
                file_data.append({"filename": file.filename, "content": content})

            task_ids, date_dir = service.process_files(file_data)

            for task_id, fd in zip(task_ids, file_data):
                file_dir = os.path.join(date_dir, task_id)
                import_file_path = os.path.join(file_dir, fd["filename"])
                background_tasks.add_task(_run_import_task, task_id, file_dir, import_file_path)

            return UploadResponse(task_ids=task_ids)
        except Exception as e:
            logger.error(f"上传失败: {e}\n{traceback.format_exc()}")
            from fastapi.responses import JSONResponse
            return JSONResponse(status_code=500, content={"detail": str(e)})

    @app.get("/status/{task_id}", response_model=TaskStatusResponse)
    async def get_task(task_id: str):
        task_info = TaskService.get_task_info(task_id)
        return TaskStatusResponse(**task_info)


def _run_import_task(task_id: str, file_dir: str, import_file_path: str):
    service = get_file_import_service()
    service.run_import_task(task_id, file_dir, import_file_path)


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
