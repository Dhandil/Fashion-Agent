from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage

from app.agents.nodes.retrieve_knowledge import (
    create_retrieve_knowledge_node,
)
from app.agents.state.shopping import ShoppingAgentState
from app.rag.loaders.text_splitter import create_text_splitter
from app.rag.releases.ingestion import (
    prepare_release_fragments,
    synchronize_prepared_release,
)
from app.rag.releases.loader import load_knowledge_release
from app.rag.vectorstores.chroma import (
    create_chroma_vector_store,
)


class KeywordEmbeddings(Embeddings):
    """用可预测的关键词向量验证 Chroma 检索，不请求外部模型。"""

    @staticmethod
    def _embed(text: str) -> list[float]:
        """把亚麻和羊毛映射到不同向量方向。"""

        return [
            1.0 if "亚麻" in text else 0.0,
            1.0 if "羊毛" in text else 0.0,
            0.1,
        ]

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """为待写入的知识片段生成测试向量。"""

        return [
            self._embed(text)
            for text in texts
        ]

    def embed_query(self, text: str) -> list[float]:
        """为检索问题生成测试向量。"""

        return self._embed(text)


def _knowledge_markdown(
    *,
    knowledge_id: str,
    title: str,
    content: str,
    source_id: str,
) -> str:
    """生成一篇符合发布规范的最小知识文档。"""

    return f"""---
knowledge_id: {knowledge_id}
title: {title}
doc_type: material_guide
status: approved
version: 1.0.0
updated_at: 2026-07-31
source_ids: [{source_id}]
runtime:
  publish_to_rag: true
tags: [{title.removesuffix("指南")}, 面料]
---

# {title}

## S01 核心结论

{content}
"""


def test_manifest_import_can_be_retrieved_with_hit_source(
    tmp_path: Path,
) -> None:
    """验证 Manifest 入库、Chroma 检索和逐命中来源形成完整链路。"""

    knowledge_root = tmp_path / "Fashion-Agent-Knowledge"
    knowledge_directory = (
        knowledge_root / "knowledge" / "01_materials"
    )
    knowledge_directory.mkdir(parents=True)

    documents = (
        (
            "fk-materials-linen-test",
            "linen.md",
            "亚麻指南",
            "亚麻适合炎热天气和夏季通勤。",
            "SRC-0001",
        ),
        (
            "fk-materials-wool-test",
            "wool.md",
            "羊毛指南",
            "羊毛适合寒冷天气并需要关注护理。",
            "SRC-0002",
        ),
    )

    manifest_entries: list[str] = []
    for (
        knowledge_id,
        file_name,
        title,
        content,
        source_id,
    ) in documents:
        document_path = knowledge_directory / file_name
        document_path.write_text(
            _knowledge_markdown(
                knowledge_id=knowledge_id,
                title=title,
                content=content,
                source_id=source_id,
            ),
            encoding="utf-8",
        )
        relative_path = (
            f"knowledge/01_materials/{file_name}"
        )
        manifest_entries.append(
            "\n".join(
                (
                    f"  - knowledge_id: {knowledge_id}",
                    "    version: 1.0.0",
                    f"    path: {relative_path}",
                    (
                        "    content_sha256: "
                        f"{sha256(document_path.read_bytes()).hexdigest()}"
                    ),
                ),
            ),
        )

    manifest_path = (
        knowledge_root
        / "releases"
        / "manifests"
        / "fashion-knowledge-test.yaml"
    )
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        "\n".join(
            (
                "release_id: fashion-knowledge-test",
                "created_at: 2026-07-31",
                "approved_by: test-reviewer",
                "approval_scope: integration-test",
                "target: fashion-agent-chroma",
                "supersedes:",
                "batch: TEST-BATCH",
                "documents:",
                *manifest_entries,
                "",
            ),
        ),
        encoding="utf-8",
    )

    # 不使用真实持久化目录，测试集合只存在于当前测试进程。
    vector_store = create_chroma_vector_store(
        embeddings=KeywordEmbeddings(),
        collection_name=f"manifest_test_{uuid4().hex}",
        persist_directory=None,
    )

    try:
        # 先放入一条不在 Manifest 中的旧示例，验证同步后会被清理。
        vector_store.add_texts(
            texts=["旧的样例知识。"],
            metadatas=[
                {
                    "source": "data/samples/fabrics.md",
                },
            ],
            ids=["legacy-sample-fragment"],
        )

        release = load_knowledge_release(
            knowledge_root=knowledge_root,
            manifest_path=manifest_path,
        )
        prepared = prepare_release_fragments(
            release=release,
            text_splitter=create_text_splitter(
                chunk_size=200,
                chunk_overlap=20,
            ),
        )
        report = synchronize_prepared_release(
            prepared=prepared,
            vector_store=vector_store,
        )

        assert report.imported_document_count == 2
        assert report.fragment_count == 2
        assert report.removed_fragment_count == 1
        assert set(vector_store.get(include=[])["ids"]) == set(
            prepared.fragment_ids,
        )

        retriever = vector_store.as_retriever(
            search_kwargs={"k": 1},
        )
        retrieve_knowledge = create_retrieve_knowledge_node(
            retriever,
        )
        state: ShoppingAgentState = {
            "messages": [
                HumanMessage(
                    content="夏天穿亚麻有什么特点？",
                ),
            ],
        }

        result = retrieve_knowledge(state)

        assert "亚麻适合炎热天气" in result[
            "knowledge_context"
        ]
        assert result["knowledge_sources"] == [
            (
                "fk-materials-linen-test::S01::001 | "
                "knowledge/01_materials/linen.md"
            ),
        ]
    finally:
        vector_store.delete_collection()
