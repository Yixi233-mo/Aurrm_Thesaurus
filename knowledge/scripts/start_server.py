#!/usr/bin/env python3
"""
知识库系统启动脚本

同时启动导入服务和查询服务：
  - 导入服务：http://localhost:8000 （文件上传 + /import）
  - 查询服务：http://localhost:8001 （问答查询 + /chat）
"""

import sys
import os
import time
import signal
import subprocess
from pathlib import Path

# 项目根目录
PROJECT_DIR = Path(__file__).resolve().parent.parent

# 确保项目可导入
sys.path.insert(0, str(PROJECT_DIR.parent))

# 加载 .env（基于文件位置，不受 CWD 影响）
from knowledge.core import env  # noqa: E402

IMPORT_HOST = os.getenv("IMPORT_HOST", "0.0.0.0")
IMPORT_PORT = int(os.getenv("IMPORT_PORT", "8000"))
QUERY_HOST = os.getenv("QUERY_HOST", "0.0.0.0")
QUERY_PORT = int(os.getenv("QUERY_PORT", "8001"))

# 使用 conda knowledge 环境的 Python
CONDA_PYTHON = r"D:\acaconda\envs\knowledge\python.exe"


def start_service(name: str, module_path: str, host: str, port: int) -> subprocess.Popen:
    """启动一个 FastAPI 服务"""
    print(f"  启动 {name} → http://{host}:{port}")

    # 设置环境变量，确保 knowledge 包可被找到
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_DIR.parent)

    proc = subprocess.Popen(
        [
            CONDA_PYTHON, "-m", "uvicorn",
            module_path,
            "--host", host,
            "--port", str(port),
            "--log-level", "info",
        ],
        cwd=str(PROJECT_DIR.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    return proc


def stream_output(proc: subprocess.Popen, name: str):
    """实时流式输出服务日志"""
    prefix = f"[{name}]"
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                print(f"  {prefix} {line}")
    except Exception:
        pass


def main():
    print("=" * 60)
    print("  金融知识库系统启动")
    print("=" * 60)

    processes = []

    try:
        # 启动导入服务
        print("\n[1/2] 启动导入服务...")
        import_proc = start_service(
            "import", "knowledge.api.import_router:app",
            IMPORT_HOST, IMPORT_PORT,
        )
        processes.append(("导入服务", import_proc))
        time.sleep(2)

        # 启动查询服务
        print("\n[2/2] 启动查询服务...")
        query_proc = start_service(
            "query", "knowledge.api.query_router:app",
            QUERY_HOST, QUERY_PORT,
        )
        processes.append(("查询服务", query_proc))
        time.sleep(2)

        # 检查进程是否存活
        print("\n" + "=" * 60)
        print("  服务状态")
        print("=" * 60)
        for name, proc in processes:
            retcode = proc.poll()
            status = "运行中" if retcode is None else f"已退出 (code={retcode})"
            print(f"  {name}: {status}")

        print("\n" + "=" * 60)
        print("  访问地址")
        print("=" * 60)
        print(f"  问答界面:  http://localhost:{QUERY_PORT}/chat")
        print(f"  导入界面:  http://localhost:{IMPORT_PORT}/import")
        print(f"  查询 API:  http://localhost:{QUERY_PORT}/query")
        print(f"  上传 API:  http://localhost:{IMPORT_PORT}/upload")
        print("=" * 60)
        print("\n  按 Ctrl+C 停止所有服务\n")

        # 实时输出日志
        while True:
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"\n  !! {name} 已停止 (code={proc.poll()})")
                    return
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n正在停止服务...")
    finally:
        for name, proc in processes:
            if proc.poll() is None:
                print(f"  停止 {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"  强制终止 {name}...")
                    proc.kill()
        print("所有服务已停止。")


if __name__ == "__main__":
    main()
