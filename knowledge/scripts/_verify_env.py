#!/usr/bin/env python3
"""验证脚本 - 在 conda knowledge 环境中运行"""
import sys
sys.path.insert(0, r'E:\work_space\掌柜智库\002')

from knowledge.core import env
import os

print('=== .env 环境变量检查 ===')
print('MILVUS_URL:', repr(os.getenv('MILVUS_URL','NOT FOUND')))
print('NEO4J_URI:', repr(os.getenv('NEO4J_URI','NOT FOUND')))
print('BGE_M3_PATH:', repr(os.getenv('BGE_M3_PATH','NOT FOUND')))
print('OPENAI_API_KEY:', 'PRESENT' if os.getenv('OPENAI_API_KEY') else 'MISSING')
print('MINERU_KEY:', 'PRESENT' if os.getenv('MINERU_KEY') else 'MISSING')
print('MONGO_URL:', repr(os.getenv('MONGO_URL','NOT FOUND')))

print()
print('=== Milvus 连接测试 ===')
from knowledge.tools.milvus_utils import get_milvus_client
client = get_milvus_client()
print('Client:', 'OK' if client else 'FAIL')
if client:
    try:
        cols = client.list_collections()
        print('Collections:', cols)
    except Exception as e:
        print(f'list_collections error: {e}')

print()
print('=== Neo4j 连接测试 ===')
from knowledge.tools.neo4j_utils import get_neo4j_driver
driver = get_neo4j_driver()
with driver.session() as s:
    r = s.run('RETURN 1 as n').data()
    print('Test query:', r)

print()
print('=== MongoDB 连接测试 ===')
from knowledge.tools.mongo_history_utils import HistoryMongoTool
tool = HistoryMongoTool()
print('MongoDB tool: OK')

print()
print('=== MinIO 连接测试 ===')
from knowledge.tools.minio_utils import get_minio_client
mc = get_minio_client()
print('MinIO client:', 'OK' if mc else 'FAIL (optional)')

print()
print('=== LLM 客户端测试 ===')
from knowledge.tools.llm_utils import get_llm_client
llm = get_llm_client()
print('LLM client:', 'OK' if llm else 'FAIL')
if llm:
    try:
        resp = llm.invoke('你好，请用一句话回复')
        print('LLM response:', resp.content[:100])
    except Exception as e:
        print(f'LLM invoke error: {e}')

print()
print('=== BGE-M3 模型测试 ===')
from knowledge.tools.embedding_utils import get_bge_m3_model
ef = get_bge_m3_model()
print('BGE-M3 model:', 'OK' if ef else 'FAIL')
if ef:
    vecs = ef.encode_documents(['test'])
    print(f'  Dense dim: {len(vecs["dense"][0])}, Sparse nnz: {len(vecs["sparse"].data)}')

print()
print('=== pymilvus.model 模块检查 ===')
try:
    from pymilvus.model.hybrid import BGEM3EmbeddingFunction
    print('pymilvus.model.hybrid: OK')
except ImportError as e:
    print(f'pymilvus.model.hybrid: MISSING - {e}')

print()
print('=== 导入流程图加载测试 ===')
from knowledge.processor.import_process.main_graph import kb_import_app
print('kb_import_app:', 'OK' if kb_import_app else 'FAIL')

print()
print('=== 全部验证完成 ===')
