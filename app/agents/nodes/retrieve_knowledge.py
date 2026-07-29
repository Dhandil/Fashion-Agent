from collections.abc import Callable

from langchain_core.retrievers import BaseRetriever

from app.agents.state.shopping import ShoppingAgentState


def create_retrieve_knowledge_node(
    retriever: BaseRetriever,
) -> Callable[[ShoppingAgentState], dict[str, str | list[str]]]:
    """创建已经绑定 Retriever 的知识检索节点。"""

    def retriever_knowledge(
        state: ShoppingAgentState,
    ) -> dict[str, str | list[str]]:
        """根据最新用户消息检索服装知识。"""

        # 读取当前 State 中的最后一条消息
        latest_message = state["messages"][-1]

        # 将消息内容转换成检索查询字符串
        query = str(latest_message.content)

        # 从向量库检索相关知识文档
        documents = retriever.invoke(query)

        # 将多个文档片段组合成模型可阅读的上下文
        knowledge_context = "\n\n".join(
            document.page_content
            for document in documents
        )

        # 从文档 metadata 中提取来源，并保持顺序去重
        knowledge_sources = list(
            dict.fromkeys(
                str(document.metadata["source"])
                for document in documents
                if document.metadata.get("source")
            )
        )

        return {
            "knowledge_context": knowledge_context,
            "knowledge_sources": knowledge_sources,
        }

    return retriever_knowledge