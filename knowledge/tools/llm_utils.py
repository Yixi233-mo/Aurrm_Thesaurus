import os, logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from knowledge.core import env  # noqa: F401 - 加载项目根目录 .env
from langchain_openai import ChatOpenAI
import threading

cache_llm_client = {}

# 全局信号量：限制同时发向 LLM 服务的请求数，避免触发 429 (limit=10)
LLM_CONCURRENT_LIMIT = 5
_llm_semaphore = threading.Semaphore(LLM_CONCURRENT_LIMIT)


class _LLMClientWrapper:
    """ wraps ChatOpenAI and limits concurrency via a module-level semaphore.

    所有 invoke / batch 调用都会先获取信号量，确保同时发起请求数不超过 LLM_CONCURRENT_LIMIT。
    """

    def __init__(self, client: ChatOpenAI):
        self._client = client

    def invoke(self, *args, **kwargs):
        with _llm_semaphore:
            return self._client.invoke(*args, **kwargs)

    def batch(self, *args, **kwargs):
        with _llm_semaphore:
            return self._client.batch(*args, **kwargs)

    def stream(self, *args, **kwargs):
        with _llm_semaphore:
            yield from self._client.stream(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._client, name)


def _detect_provider(api_base: str) -> str:
    """根据 API base URL 自动识别提供商。"""
    base = api_base.lower()
    if "dashscope" in base:
        return "dashscope"
    if "deepseek" in base:
        return "deepseek"
    if "openai.com" in base:
        return "openai"
    if "bigmodel" in base or "zhipu" in base:
        return "zhipu"
    if "api.stepfun" in base:
        return "stepfun"
    return "custom"


def _default_model_for(provider: str) -> str:
    """根据提供商返回默认模型名。"""
    return {
        "dashscope": "qwen-plus",
        "deepseek": "deepseek-chat",
        "openai": "gpt-4o",
        "zhipu": "glm-4-flash",
        "stepfun": "step-2-16k",
    }.get(provider, "qwen-plus")


def get_llm_client(mode_name: str = None, temperature: float = 0.0, response_format: bool = False):
    """
    Returns: 返回LLM客户端对象
    缓存的对象是：client
    缓存的key: 不同的节点用不同的模型以及同一个节点用不同响应格式

    配置来源（按优先级）:
      - mode_name 参数 → 最高优先级
      - .env 中 LLM_MODEL / ITEM_MODEL → 根据 API base 自动匹配默认模型
      - 根据 OPENAI_API_BASE 自动识别提供商:
          dashscope → qwen-plus
          deepseek  → deepseek-chat
          openai    → gpt-4o
          zhipuai   → glm-4-flash
          stepfun   → step-2-16k
    """

    # 1. 从 .env 读取 API 配置（key 和 base 都必须存在，无 fallback）
    api_base = os.getenv('OPENAI_API_BASE')
    api_key = os.getenv('OPENAI_API_KEY')

    missing = []
    if not api_base:
        missing.append("OPENAI_API_BASE")
    if not api_key:
        missing.append("OPENAI_API_KEY")
    if missing:
        logger.error(f"缺少环境变量: {', '.join(missing)}，请在 .env 中配置")
        return None

    # 2. 模型名优先级：mode_name > LLM_DEFAULT_MODEL > ITEM_MODEL > 自动检测
    provider = _detect_provider(api_base)
    model_name = (
        mode_name
        or os.getenv('LLM_DEFAULT_MODEL')
        or os.getenv('ITEM_MODEL')
        or _default_model_for(provider)
    )

    cache_key = (mode_name, response_format)

    # 3. 缓存命中 直接返回（wrapper 可重复包裹，幂等）
    if cache_key in cache_llm_client:
        return cache_llm_client[cache_key]

    # 3. 返回的内容格式
    model_kwargs = {}
    if response_format:
        model_kwargs['response_format'] = {"type": "json_object"}
    try:
        # 4. 定义模型实例
        client = ChatOpenAI(
            model_name=model_name,
            openai_api_key=api_key,
            openai_api_base=api_base,
            temperature=temperature,
            extra_body={"enable_thinking": False},
            model_kwargs=model_kwargs,
            openai_proxy=None,       # 禁用系统代理，避免 Connection error
        )

        # 5. 用信号量包装后缓存
        wrapped = _LLMClientWrapper(client)
        cache_llm_client[cache_key] = wrapped

        # 6. 返回
        return wrapped
    except Exception as e:
        logger.error(f"LLM客户端创建失败,原因:{str(e)}")
        return None


if __name__ == '__main__':
    import json

    llm_client = get_llm_client()
    if llm_client is None:
        print("LLM 客户端初始化失败，请检查 .env 配置")
    else:
        ai_message = llm_client.invoke("你好，请问你是谁?")
        print(ai_message.content)
