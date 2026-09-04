# ========== download_bge_reranker.py ==========
import os
from modelscope.hub.snapshot_download import snapshot_download

# 读取环境变量（确保 .env 已加载）
from dotenv import load_dotenv
load_dotenv()

cache_dir = os.getenv("MODELSCOPE_CACHE", "./modelscope_cache")

print("正在下载 BGE-Reranker-Large ...")
model_dir = snapshot_download(
    model_id="BAAI/bge-reranker-large",
    cache_dir=cache_dir,
    revision="master",
    ignore_file_pattern=[".git", ".py", ".md"]  # 忽略非必要文件
)
print(f"模型已下载至: {model_dir}")