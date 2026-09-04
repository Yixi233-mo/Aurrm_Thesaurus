"""
图片处理核心流程迷你版 (Mini MdImg Node)
覆盖：MinIO 连接、VLM 调用、Markdown 替换
"""
import os
import re
import base64
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
from collections import deque
import os

# 获取系统环境变量



# ---------- 1. 基础配置 ----------
@dataclass
class MiniConfig:
    minio_endpoint: str = "192.168.2.169:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "knowledge-base"
    minio_secure: bool = False
    vl_model: str = "qwen-vl-plus"
    vl_api_key: str = "your-api-key"  # 需替换为实际值
    vl_api_base: str = "https://api.example.com/v1"
    requests_per_minute: int = 10

# ---------- 2. MinIO 工具类 ----------
class MiniMinioClient:
    def __init__(self, config: MiniConfig):
        self.config = config
        self.client = None
        self._connect()

    def _connect(self):
        """建立 MinIO 连接"""
        try:
            from minio import Minio
            self.client = Minio(
                self.config.minio_endpoint,
                access_key=self.config.minio_access_key,
                secret_key=self.config.minio_secret_key,
                secure=self.config.minio_secure
            )
            # 确保 bucket 存在
            if not self.client.bucket_exists(self.config.minio_bucket):
                self.client.make_bucket(self.config.minio_bucket)
            print(f"✅ MinIO 连接成功: {self.config.minio_bucket}")
        except Exception as e:
            print(f"❌ MinIO 连接失败: {e}")
            self.client = None

    def upload_file(self, local_path: str, object_name: str) -> str:
        """上传文件并返回访问 URL"""
        if not self.client:
            return f"http://mock-minio/{object_name}"

        try:
            # 确定 content-type
            ext = os.path.splitext(local_path)[1].lower()
            content_type = f"image/{ext[1:]}" if ext.startswith(".") else "application/octet-stream"

            self.client.fput_object(
                self.config.minio_bucket,
                object_name,
                local_path,
                content_type=content_type
            )
            # 构造访问 URL
            protocol = "https" if self.config.minio_secure else "http"
            url = f"{protocol}://{self.config.minio_endpoint}/{self.config.minio_bucket}/{object_name}"
            return url
        except Exception as e:
            print(f"⚠️ 上传失败: {e}")
            return f"http://mock-minio/{object_name}"

# ---------- 3. VLM 调用 ----------
class MiniVLMClient:
    def __init__(self, config: MiniConfig):
        self.config = config
        self.request_timestamps = deque()
        self._init_client()

    def _init_client(self):
        """初始化 OpenAI 兼容客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.config.vl_api_key,
                base_url=self.config.vl_api_base
            )
        except Exception as e:
            print(f"❌ VLM 客户端初始化失败: {e}")
            self.client = None

    def _enforce_rate_limit(self, window_seconds: int = 60):
        """滑动窗口速率限制"""
        current_time = time.time()
        while self.request_timestamps and current_time - self.request_timestamps[0] >= window_seconds:
            self.request_timestamps.popleft()

        if len(self.request_timestamps) >= self.config.requests_per_minute:
            sleep_time = window_seconds - (current_time - self.request_timestamps[0])
            if sleep_time > 0:
                print(f"⏳ 速率限制中，等待 {sleep_time:.2f}s")
                time.sleep(sleep_time)
            # 清理过期时间戳
            current_time = time.time()
            while self.request_timestamps and current_time - self.request_timestamps[0] >= window_seconds:
                self.request_timestamps.popleft()

        self.request_timestamps.append(time.time())

    def generate_summary(self, image_path: str, context: str = "") -> str:
        """为图片生成摘要"""
        if not self.client:
            return "图片描述（无客户端）"

        self._enforce_rate_limit()

        # 读取并编码图片
        try:
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            print(f"⚠️ 读取图片失败 {image_path}: {e}")
            return "图片读取失败"

        # 构造 Prompt
        prompt = f"""请为这张图片生成一个简短的中文标题。
背景上下文：{context if context else "无额外上下文"}
要求：10-20字，描述图片核心内容，不要包含"图片"二字。"""

        try:
            response = self.client.chat.completions.create(
                model=self.config.vl_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                max_tokens=50,
                temperature=0.3
            )
            summary = response.choices[0].message.content.strip().replace("\n", " ")
            return summary if summary else "图片描述"
        except Exception as e:
            print(f"⚠️ VLM 调用失败: {e}")
            return "图片描述"

# ---------- 4. 核心处理函数 ----------
def process_md_images(
    md_file_path: str,
    config: MiniConfig
) -> Tuple[str, str, Dict[str, str]]:
    """
    处理 Markdown 中的图片：提取上下文、生成摘要、上传 MinIO、替换链接

    Returns:
        Tuple[新文件路径, 新内容, {图片名: 摘要}]
    """
    md_path = Path(md_file_path)
    images_dir = md_path.parent / "images"
    new_md_path = md_path.with_name(f"{md_path.stem}_mini{md_path.suffix}")

    print(f"\n📄 处理文件: {md_path.name}")

    # ---- Step 1: 读取 MD ----
    with open(md_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    # ---- Step 2: 扫描图片 ----
    if not images_dir.exists():
        print("⚠️ images 目录不存在，跳过处理")
        return str(new_md_path), md_content, {}

    print(f"📁 图片目录: {images_dir}")

    minio = MiniMinioClient(config)
    vlm = MiniVLMClient(config)

    # 提取所有图片引用
    pattern = r"!\[(.*?)\]\((.*?)\)"
    image_matches = list(re.finditer(pattern, md_content))

    if not image_matches:
        print("ℹ️ 未找到图片引用")
        return str(new_md_path), md_content, {}

    summaries = {}
    new_md_content = md_content

    # ---- Step 3: 逐张处理 ----
    for idx, match in enumerate(image_matches):
        alt_text = match.group(1)
        img_path = match.group(2)

        # 只处理本地图片（相对路径）
        if img_path.startswith(("http://", "https://")):
            print(f"  ⏭️ 跳过远程图片: {img_path}")
            continue

        # 解析文件名
        img_filename = Path(img_path).name
        local_img_path = images_dir / img_filename

        if not local_img_path.exists():
            print(f"  ⚠️ 本地图片不存在: {local_img_path}")
            continue

        print(f"\n🖼️ [{idx+1}] 处理: {img_filename}")

        # 提取上下文（简化版：取前后各2行）
        lines = md_content.split("\n")
        line_idx = -1
        for i, line in enumerate(lines):
            if img_filename in line and "![" in line:
                line_idx = i
                break

        context_before = "\n".join(lines[max(0, line_idx-2):line_idx]) if line_idx > 0 else ""
        context_after = "\n".join(lines[line_idx+1:min(len(lines), line_idx+3)]) if line_idx >= 0 else ""
        context = f"上文: {context_before[:100]}... 下文: {context_after[:100]}..."

        # 生成摘要
        summary = vlm.generate_summary(str(local_img_path), context)
        summaries[img_filename] = summary
        print(f"  ✅ 摘要: {summary}")

        # 上传到 MinIO
        object_name = f"{md_path.stem}/{img_filename}"
        remote_url = minio.upload_file(str(local_img_path), object_name)
        print(f"  📤 上传至: {remote_url}")

        # 替换 Markdown 链接
        old_pattern = re.escape(img_path)
        new_md_content = re.sub(
            r"!\[(.*?)\]\(" + old_pattern + r"\)",
            f"![{summary}]({remote_url})",
            new_md_content
        )

    # ---- Step 4: 写入新文件 ----
    with open(new_md_path, "w", encoding="utf-8") as f:
        f.write(new_md_content)

    print(f"\n✅ 处理完成，新文件: {new_md_path}")
    return str(new_md_path), new_md_content, summaries


# ---------- 5. 运行测试 ----------
if __name__ == "__main__":
    print("=" * 60)
    print("图片处理与 MinIO 上传节点 · 迷你版")
    print("=" * 60)

    # 配置（请修改为实际值）
    config = MiniConfig(
        minio_endpoint="localhost:9000",           # 修改为实际地址
        minio_access_key="minioadmin",
        minio_secret_key="minioadmin",
        vl_api_key="***REDACTED***",                       # 替换为真实 API Key
        vl_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",  # 示例：通义千问
        vl_model="qwen-vl-plus",                   # 视觉模型
        requests_per_minute=10
    )

    # 模拟测试路径（请替换为实际文件路径）
    TEST_MD_PATH = "./test_data/万用表的使用.md"  # 修改为实际路径

    # 创建测试目录和示例文件
    os.makedirs("./test_data/images", exist_ok=True)
    test_md_content = """# 万用表的使用

万用表是一种多功能测量仪器。

![](images/image_0.png)

上图展示了万用表的正面外观，可以看到显示屏和旋钮。

## 功能说明

万用表可以测量电压、电流和电阻。

![](images/image_1.png)

这是万用表的背面板，显示电池仓和保险丝位置。
"""
    with open(TEST_MD_PATH, "w", encoding="utf-8") as f:
        f.write(test_md_content)

    # 创建占位图片（实际应放置真实图片）
    # 这里仅做演示，实际运行时请放置真实图片
    print("ℹ️ 请确保 ./test_data/images/ 目录下存在真实图片文件")
    print("ℹ️ 或修改 TEST_MD_PATH 为真实文档路径\n")

    # 执行处理
    new_path, content, summaries = process_md_images(TEST_MD_PATH, config)

    print("\n" + "=" * 60)
    print("处理结果摘要")
    print("=" * 60)
    print(f"新文件路径: {new_path}")
    print(f"摘要数量: {len(summaries)}")
    for name, summary in summaries.items():
        print(f"  - {name}: {summary}")