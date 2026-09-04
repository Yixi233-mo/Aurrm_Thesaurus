# knowledge/core/env.py
"""
统一加载 .env，基于本文件所在项目根目录自动定位，不受 CWD 影响。
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ==================== 兼容 torch meta tensor 限制 ====================
# FlagEmbedding / accelerate 在 CUDA 上使用 meta tensor 延迟初始化，
# 导致 "Cannot copy out of meta tensor" 错误。
# 设置此环境变量禁用 meta tensor 初始化。
os.environ.setdefault('ACCELERATE_DISABLE_META_INIT', '1')

# ==================== 兼容 torch 2.4.x 的 CVE 限制 ====================
# torch >= 2.6 在 torch.load 中强制要求 weights_only=True（CVE-2025-32434）。
# torch 2.4.x 默认 weights_only=None，会被新逻辑拒绝加载 .bin 模型文件。
# 这里在最早期 monkey-patch torch.load，强制 weights_only=False。
# torch >= 2.6 不再需要此补丁。
_torch_patched = False

def _patch_torch_load():
    global _torch_patched
    if _torch_patched:
        return
    try:
        import torch
        if hasattr(torch, 'load'):
            _orig = torch.load
            def _patched_load(f, map_location=None, pickle_module=None, *, weights_only=None, mmap=None, **kwargs):
                if weights_only is None:
                    weights_only = False
                return _orig(f, map_location, pickle_module, weights_only=weights_only, mmap=mmap, **kwargs)
            torch.load = _patched_load
            _torch_patched = True
    except Exception:
        pass

_patch_torch_load()
# ====================================================================

# knowledge/core/env.py → parent=core, parent.parent=knowledge
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

load_dotenv(_ENV_FILE, override=True)
