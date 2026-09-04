# knowledge/tools/minio_utils.py

import os
from minio import Minio

from knowledge.core import env  # noqa: F401 - 加载项目根目录 .env

# MinIO 配置（支持环境变量覆盖）
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "111.228.53.183:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "knowledge-base")


# 初始化 MinIO 客户端
try:
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False  # 本地开发不使用 HTTPS
    )
    # 确保 Bucket 存在
    if not minio_client.bucket_exists(MINIO_BUCKET_NAME):
        minio_client.make_bucket(MINIO_BUCKET_NAME)
except Exception as e:
    print(f"MinIO initialization failed: {e}")
    minio_client = None


def get_minio_client():
    """获取 MinIO 客户端单例"""
    return minio_client