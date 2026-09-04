# ========== verify_models.py ==========
import os
from dotenv import load_dotenv

load_dotenv()

# 获取配置路径
reranker_path = os.getenv("BGE_RERANKER_LARGE")
m3_path = os.getenv("BGE_M3_PATH")
cache_dir = os.getenv("MODELSCOPE_CACHE")

print("=== 模型文件检查 ===\n")

def check_path(path, name):
    if path and os.path.exists(path):
        files = os.listdir(path)
        print(f"✅ {name}: {path} (包含 {len(files)} 个文件)")
    else:
        print(f"❌ {name}: 路径不存在或未配置")

check_path(reranker_path, "BGE-Reranker-Large")
check_path(m3_path, "BGE-M3")
check_path(cache_dir, "ModelScope 缓存目录")

print("\n如需从 HuggingFace 补充下载，请将 MINERU_MODEL_SOURCE 改为 huggingface")