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


def get_llm_client(mode_name: str = None, temperature: float = 0.0, response_format: bool = False):
    """

    Returns: 返回LLM客户端对象
    # 自己加的提供:dashscope
    # 兼容OpenAI: LangChain LangGraph(集成OpenAI)
    缓存的对象是：client
    缓存的key: 不同的节点用不同的模型以及同一个节点用不同响应格式
    """

    # 1. 获取模型的名字
    model_name = mode_name or os.getenv('ITEM_MODEL', "qwen-flash")
    api_key = os.getenv('OPENAI_API_KEY', "***REDACTED***")
    api_base = os.getenv('OPENAI_API_BASE', "https://dashscope.aliyuncs.com/compatible-mode/v1")

    cache_key = (mode_name, response_format)  # 复合缓存key(a,b)

    # 2. 缓存命中 直接返回（wrapper 可重复包裹，幂等）
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
            model_kwargs=model_kwargs
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
    llm_client = get_llm_client(mode_name="qwen-flash", response_format=False)

    import json

    # ai_message = llm_client.invoke("你好，请问您是谁?")
    # 使用本质发送请求（底层将model_kwargs的所有参数都在发送请求之前拼接到请求体身上）
    ai_message = llm_client.invoke("您好，请给我讲一个笑话，返回json格式：{\"key\":\"value\"}")
    print(ai_message.content)

    # json对象 json字符串
    json_object = json.loads(ai_message.content)
