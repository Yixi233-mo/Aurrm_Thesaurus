"""闲聊节点

当 LLM 意图识别判定为闲聊时，直接调用大模型进行智能对话，
无需检索知识库。支持多轮对话历史上下文。
"""

from typing import List, Dict

from knowledge.processor.query_process.base import BaseNode, setup_logging
from knowledge.processor.query_process.state import QueryGraphState
from knowledge.tools.llm_utils import get_llm_client
from knowledge.tools.sse_utils import push_sse_event, SSEEvent
from knowledge.tools.mongo_history_utils import get_recent_messages, save_chat_message


CHAT_SYSTEM_PROMPT = """你是「掌柜智库」的智能问答助手，由 AURUM THESAURUS 驱动。

你不仅仅是一个金融知识检索工具，更是一个可以自然交流的智能伙伴。
当用户进行闲聊、问候、表达情绪或提出一般性问题时，你可以:
- 友好、自然地回应
- 适当使用 emoji，保持轻松愉快的语气
- 在对话中灵活展现个性和幽默感
- 主动引导用户，让他们知道你也可以帮忙查询金融产品相关信息

如果用户的问题转向金融知识查询，你可以简要回应并引导他们详细提问。

请用中文回答，保持简洁、亲切、自然。"""


class ChatNode(BaseNode):
    """闲聊节点。

    调用 LLM 进行智能对话，无需检索知识库。
    支持流式输出和非流式输出。
    """

    name = "chat"

    def process(self, state: QueryGraphState) -> QueryGraphState:
        session_id = state.get("session_id", "")
        is_stream = state.get("is_stream", False)
        original_query = state.get("original_query", "")

        # 1. 获取历史对话
        chat_history = get_recent_messages(session_id, limit=10)
        history_text = self._format_history(chat_history)

        # 2. 构建消息列表
        messages = self._build_messages(original_query, history_text)

        # 3. 调用 LLM
        llm_client = get_llm_client()
        if llm_client is None:
            state["answer"] = "抱歉，我现在无法正常响应，请稍后再试。"
            state["skip_retrieval"] = True
            return state

        if is_stream:
            state["answer"] = self._stream_generate(llm_client, messages, session_id)
        else:
            state["answer"] = self._invoke_generate(llm_client, messages)

        state["skip_retrieval"] = True

        # 4. 写入历史记录
        self._write_history(session_id, original_query, state["answer"])

        return state

    def _build_messages(self, query: str, history_text: str) -> List[Dict]:
        """构建 LLM 消息列表。"""
        messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]

        # 添加历史对话
        if history_text:
            for line in history_text.strip().split("\n"):
                if line.startswith("用户: "):
                    messages.append({"role": "user", "content": line[4:]})
                elif line.startswith("助手: "):
                    messages.append({"role": "assistant", "content": line[4:]})

        # 添加当前问题
        messages.append({"role": "user", "content": query})

        return messages

    def _invoke_generate(self, llm_client, messages: List[Dict]) -> str:
        """非流式生成。"""
        try:
            from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

            lc_messages = []
            for m in messages:
                if m["role"] == "system":
                    lc_messages.append(SystemMessage(content=m["content"]))
                elif m["role"] == "user":
                    lc_messages.append(HumanMessage(content=m["content"]))
                elif m["role"] == "assistant":
                    lc_messages.append(AIMessage(content=m["content"]))

            response = llm_client.invoke(lc_messages)
            return (response.content or "").strip()
        except Exception as e:
            self.logger.error(f"闲聊 LLM 调用失败: {e}")
            return "抱歉，我现在有点困惑，能再说一遍吗？"

    def _stream_generate(self, llm_client, messages: List[Dict], session_id: str) -> str:
        """流式生成，逐 token 推送 delta 事件。"""
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        lc_messages = []
        for m in messages:
            if m["role"] == "system":
                lc_messages.append(SystemMessage(content=m["content"]))
            elif m["role"] == "user":
                lc_messages.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                lc_messages.append(AIMessage(content=m["content"]))

        accumulated = ""
        try:
            push_sse_event(session_id, SSEEvent.PROGRESS, {
                "done_list": ["意图识别"],
                "running_list": ["智能对话"],
            })
            for chunk in llm_client.stream(lc_messages):
                delta = getattr(chunk, "content", "") or ""
                if delta:
                    accumulated += delta
                    push_sse_event(session_id, SSEEvent.DELTA, {"delta": delta})
        except Exception as e:
            self.logger.error(f"闲聊流式生成失败: {e}")

        return accumulated

    @staticmethod
    def _format_history(chat_history: List[Dict]) -> str:
        """格式化历史对话为文本。"""
        lines = []
        for msg in chat_history:
            role = msg.get("role", "")
            text = msg.get("text", "")
            if role == "user":
                lines.append(f"用户: {text}")
            elif role == "assistant":
                lines.append(f"助手: {text}")
        return "\n".join(lines)

    def _write_history(self, session_id: str, user_text: str, assistant_text: str):
        """写入对话历史。"""
        try:
            save_chat_message(session_id=session_id, role="user", text=user_text)
            save_chat_message(session_id=session_id, role="assistant", text=assistant_text)
        except Exception as e:
            self.logger.warning(f"写入闲聊历史失败: {e}")


_node_instance = ChatNode()


def node_chat(state: QueryGraphState) -> QueryGraphState:
    return _node_instance(state)


if __name__ == "__main__":
    setup_logging()

    test_state = {
        "session_id": "test_chat",
        "original_query": "你好呀，今天心情不错！",
        "is_stream": False,
        "answer": "",
    }
    result = node_chat(test_state)
    print(f"回答: {result['answer']}")
