"""路径配置模块"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# knowledge 包目录
KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent

# 加载 .env（位于 knowledge 包目录下）
load_dotenv(KNOWLEDGE_DIR / ".env")

# 前端页面目录
FRONT_PAGE_DIR = KNOWLEDGE_DIR / "front"


def get_front_page_dir() -> str:
    """获取前端页面目录"""
    return str(FRONT_PAGE_DIR)


def get_temp_root() -> str:
    """获取临时文件根目录（每次调用时从环境变量读取，确保 .env 生效）"""
    temp_root = Path(os.getenv("MD_ROOT_DIR", "./temp-files/"))
    temp_root.mkdir(parents=True, exist_ok=True)
    return str(temp_root)


def get_upload_dir() -> str:
    """获取上传文件目录"""
    upload_dir = Path(os.getenv("MD_ROOT_DIR", "./temp-files/")) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return str(upload_dir)
