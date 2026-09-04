"""闲聊节点"""

from knowledge.processor.query_process.base import BaseNode
from knowledge.processor.query_process.state import QueryGraphState


CHAT_RESPONSES = [
    "你好！我是「掌柜智库」的智能问答助手，有什么可以帮助你的吗？",
    "你好呀！欢迎来到掌柜智库，我可以帮你查询金融产品的相关信息。",
    "嗨！我是你的金融知识助手，有任何关于理财产品、基金、年报等问题都可以问我。",
]


class ChatNode(BaseNode):
    """闲聊节点。

    当 LLM 判定用户意图为闲聊时，直接返回友好回复，无需检索。
    """

    name = "chat"

    def process(self, state: QueryGraphState) -> QueryGraphState:
        import random

        response = random.choice(CHAT_RESPONSES)
        state["answer"] = response
        state["skip_retrieval"] = True
        return state


_node_instance = ChatNode()


def node_chat(state: QueryGraphState) -> QueryGraphState:
    return _node_instance(state)


if __name__ == "__main__":
    from knowledge.processor.query_process.base import setup_logging

    setup_logging()

    test_state = {
        "session_id": "test_001",
        "original_query": "你好，今天天气真好！",
        "answer": "",
    }
    result = node_chat(test_state)
    print(f"回答: {result['answer']}")
