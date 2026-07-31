from collections.abc import Callable

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.agents.state.shopping import ShoppingAgentState


def _format_knowledge_source(
    document: Document,
) -> str | None:
    """生成一条可追溯到具体命中片段的知识来源。"""

    fragment_id = document.metadata.get("fragment_id")
    source_path = (
        document.metadata.get("source_path_or_url")
        or document.metadata.get("source")
    )

    if fragment_id and source_path:
        return f"{fragment_id} | {source_path}"
    if fragment_id:
        return str(fragment_id)
    if source_path:
        return str(source_path)
    return None


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

        # 每个命中片段都输出一条来源，方便核对检索依据
        knowledge_sources = [
            source
            for document in documents
            if (
                source := _format_knowledge_source(
                    document,
                )
            )
        ]

        return {
            "knowledge_context": knowledge_context,
            "knowledge_sources": knowledge_sources,
        }

    return retriever_knowledge
