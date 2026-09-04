"""
掌柜智库知识库处理包

提供文档导入、向量化、知识图谱构建等核心能力。
"""

__version__ = "0.1.0"
__author__ = "Shopkeeper Brain Team"
__description__ = "Knowledge base import & retrieval pipeline"

# 延迟导入子包，避免启动时触发重型依赖（Milvus/Neo4j/LLM客户端）
def __getattr__(name: str):
    if name == "processor":
        from . import processor
        return processor
    if name == "tools":
        from . import tools
        return tools
    raise AttributeError(f"module 'knowledge' has no attribute '{name}'")

__all__ = ["__version__", "__author__", "__description__", "processor", "tools"]