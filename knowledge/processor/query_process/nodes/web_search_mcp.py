"""MCP 网络搜索节点

通过 Parallel.ai MCP Streamable HTTP 协议调用 web_search 工具获取外部信息。
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any

from knowledge.processor.query_process.base import BaseNode, setup_logging
from knowledge.processor.query_process.state import QueryGraphState

logger = logging.getLogger(__name__)

# Parallel.ai MCP 配置（环境变量可覆盖）
PARALLEL_MCP_URL = os.getenv("PARALLEL_MCP_URL", "https://search.parallel.ai/mcp")


def _run_async(coro):
    """在同步上下文中运行 async 协程。"""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class WebSearchMcpNode(BaseNode):
    """Parallel.ai MCP 网络搜索节点。

    通过 MCP Streamable HTTP 协议连接到 Parallel.ai 搜索服务，
    根据用户查询获取相关的网络搜索结果。
    """

    name = "web_search_mcp"

    def process(self, state: QueryGraphState) -> QueryGraphState:
        query = state.get("rewritten_query", "") or state.get("original_query", "")
        if not query:
            self.logger.warning("查询内容为空，跳过网络搜索")
            return {}

        self.log_step("step_1", f"获取查询内容: {query}")

        try:
            docs = self._parallel_search(query)
            self.log_step("step_2", f"搜索完成，返回 {len(docs)} 条结果")
        except Exception as e:
            self.logger.error(f"MCP 搜索失败: {e}")
            docs = []

        if docs:
            return {"web_search_docs": docs}
        return {}

    def _parallel_search(self, query: str) -> List[Dict[str, Any]]:
        """调用 Parallel.ai MCP web_search 工具。"""
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        async def _call():
            try:
                return await asyncio.wait_for(
                    _do_call(), timeout=15.0
                )
            except asyncio.TimeoutError:
                self.logger.warning("MCP web_search 超时（15s）")
                return []

        async def _do_call():
            async with streamable_http_client(PARALLEL_MCP_URL) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    result = await session.call_tool(
                        "web_search",
                        arguments={
                            "objective": query,
                            "search_queries": [query],
                        },
                    )

                    docs = []
                    for content in result.content:
                        if content.type != "text":
                            continue
                        try:
                            data = json.loads(content.text)
                        except (json.JSONDecodeError, ValueError):
                            continue

                        for item in data.get("results", []):
                            excerpts = item.get("excerpts") or []
                            snippet = excerpts[0] if excerpts else ""
                            if not snippet:
                                continue
                            # 统一使用 "content" 字段名，与下游 rerank 节点的本地文档保持一致
                            docs.append({
                                "title": (item.get("title") or "").strip(),
                                "url": (item.get("url") or "").strip(),
                                "content": snippet.strip(),
                            })

                    return docs

        return _run_async(_call())


_node_instance = WebSearchMcpNode()


def node_web_search_mcp(state: QueryGraphState) -> QueryGraphState:
    return _node_instance(state)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    try:
        setup_logging()
    except Exception:
        import logging
        logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("开始测试: Parallel.ai MCP 网络搜索节点")
    print("=" * 60)

    test_state = {
        "original_query": "数字万用表怎么测电压？",
        "rewritten_query": "数字万用表怎么测电压？",
    }

    print(f"查询: {test_state['rewritten_query']}")
    print("-" * 60)

    try:
        result = node_web_search_mcp(test_state)
        docs = result.get("web_search_docs", [])
        if not docs:
            print("\n搜索执行完成，但未返回任何结果。")
        else:
            print(f"\n共搜索到 {len(docs)} 条相关内容:")
            for i, doc in enumerate(docs, 1):
                print(f"[{i}] {doc.get('title', '无标题')}")
                print(f"    {doc.get('content', '')[:100]}...")
                print(f"    url: {doc.get('url', '')}")
    except Exception as e:
        print(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()
