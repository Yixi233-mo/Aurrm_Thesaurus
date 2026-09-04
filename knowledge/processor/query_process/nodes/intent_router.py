"""意图路由节点

使用 LLM 对用户查询进行意图分类：
  - chat      : 闲聊，无需检索
  - web_search: 需要联网搜索
  - rag       : 需要知识库检索（默认）
"""

from knowledge.processor.query_process.base import BaseNode, setup_logging
from knowledge.processor.query_process.state import QueryGraphState, create_default_state
from knowledge.tools.llm_utils import get_llm_client


class IntentRouterNode(BaseNode):
    """意图分类节点。"""

    name = "intent_router"

    def process(self, state: QueryGraphState) -> QueryGraphState:
        query = state.get("original_query", "")
        intent = self._classify(query)
        state["intent"] = intent
        self.logger.info(f"意图识别结果: {intent} (query={query[:50]})")
        return state

    def _classify(self, query: str) -> str:
        llm = get_llm_client()
        if llm is None:
            return "rag"

        prompt = INTENT_CLASSIFY_PROMPT.format(query=query)
        response = llm.invoke(prompt)
        intent = response.content.strip().lower()

        if intent in ("chat", "web_search"):
            return intent
        return "rag"


# ==================== 路由函数 ====================

def route_after_intent(state: QueryGraphState) -> str:
    """意图分类后的路由逻辑。"""
    return state.get("intent", "rag")


# ==================== 提示词模板 ====================

INTENT_CLASSIFY_PROMPT = """你是一个意图分类器。请判断用户的查询属于以下哪种类型，只输出一个词：

1. chat —— 闲聊、打招呼、问候、表达情绪、无关金融知识的日常对话
   例如："你好"、"今天天气真好"、"谢谢"、"你是谁"

2. web_search —— 需要查询最新信息、实时数据、新闻、政策变动等知识库可能不包含的内容
   例如："今天A股大盘怎么样"、"最新利率是多少"、"最近有什么财经新闻"

3. rag —— 需要从知识库中检索金融产品说明书、招募说明书、年报、公告等文档内容
   例如："华夏债券基金的投资范围是什么"、"招商银行2026年第一季度报告说了什么"

用户查询: {query}

输出格式（只输出一个词，不要其他内容）:
chat
或
web_search
或
rag"""


# ==================== 便捷函数 ====================

_node_instance = IntentRouterNode()


def node_intent_router(state: QueryGraphState) -> QueryGraphState:
    return _node_instance(state)


# ==================== 测试 ====================

if __name__ == "__main__":
    setup_logging()

    test_queries = [
        "你好，请问你是谁？",
        "今天A股大盘走势如何？",
        "华夏债券投资基金的基本情况是什么？",
        "最新央行货币政策有什么变化？",
        "理财产品有哪些风险等级？",
    ]

    node = IntentRouterNode()
    for q in test_queries:
        state = create_default_state(original_query=q)
        result = node.process(state)
        print(f"[{result['intent']:10s}] {q}")
