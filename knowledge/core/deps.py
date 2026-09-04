"""依赖注入模块"""

from functools import lru_cache


@lru_cache()
def get_milvus_client():
    """获取 Milvus 客户端单例"""
    from knowledge.tools.milvus_utils import get_milvus_client as _get
    return _get()


@lru_cache()
def get_neo4j_driver():
    """获取 Neo4j 驱动单例"""
    from knowledge.tools.neo4j_utils import get_neo4j_driver as _get
    return _get()


@lru_cache()
def get_minio_client():
    """获取 MinIO 客户端单例"""
    from knowledge.tools.minio_utils import get_minio_client as _get
    return _get()
