# ========== download_bge_m3.py ==========
import os
from modelscope.hub.snapshot_download import snapshot_download
from dotenv import load_dotenv

load_dotenv()
cache_dir = os.getenv("MODELSCOPE_CACHE", "./modelscope_cache")

print("正在下载 BGE-M3 ...")
model_dir = snapshot_download(
    model_id="BAAI/bge-m3",
    cache_dir=cache_dir,
    revision="master"
)
print(f"模型已下载至: {model_dir}")