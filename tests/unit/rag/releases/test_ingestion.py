from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest
from langchain_core.vectorstores import VectorStore
from langchain_text_splitters.base import TextSplitter

from app.rag.releases.exceptions import KnowledgeReleaseError
from app.rag.releases.ingestion import (
    index_knowledge_release,
    prepare_release_fragments,
)
from app.rag.releases.loader import load_knowledge_release


class TwoPartTextSplitter(TextSplitter):
    """将每个章节固定切成两段，便于验证序号会按章节重置。"""

    def split_text(self, text: str) -> list[str]:
        """在文本中点切分，并始终返回两个非空片段。"""

        midpoint = max(1, len(text) // 2)
        return [text[:midpoint], text[midpoint:]]


def _build_knowledge_document(
    *,
    knowledge_id: str,
    status: str = "approved",
    publish_to_rag: bool = True,
) -> str:
    """生成导入测试使用的 Markdown 知识文档。"""

    publish_value = str(publish_to_rag).lower()
    return f"""---
knowledge_id: {knowledge_id}
title: 亚麻穿搭指南
doc_type: material_guide
status: {status}
version: 1.0.0
updated_at: 2026-07-31
source_ids:
  - SRC-0001
  - SRC-0002
runtime:
  publish_to_rag: {publish_value}
tags: [亚麻, 高温, 通勤]
---

# 亚麻穿搭指南

## S01 适用场景

亚麻面料适合炎热天气和夏季通勤。

## S02 穿着提醒

亚麻容易产生自然褶皱，需要注意日常护理。
"""


def _write_release(
    tmp_path: Path,
    *,
    documents: tuple[tuple[str, str, str, bool], ...],
    corrupt_last_hash: bool = False,
) -> tuple[Path, Path]:
    """写入测试知识库及其 Manifest。

    documents 中的每一项依次为：
    knowledge_id、Manifest 相对路径、status、publish_to_rag。
    """

    knowledge_root = tmp_path / "Fashion-Agent-Knowledge"
    manifest_entries: list[str] = []

    for index, (
        knowledge_id,
        relative_path,
        status,
        publish_to_rag,
    ) in enumerate(documents):
        document_path = knowledge_root / Path(relative_path)
        document_path.parent.mkdir(parents=True, exist_ok=True)
        document_path.write_text(
            _build_knowledge_document(
                knowledge_id=knowledge_id,
                status=status,
                publish_to_rag=publish_to_rag,
            ),
            encoding="utf-8",
        )
        content_sha256 = hashlib.sha256(
            document_path.read_bytes(),
        ).hexdigest()
        if corrupt_last_hash and index == len(documents) - 1:
            content_sha256 = "0" * 64

        manifest_entries.append(
            "\n".join(
                (
                    f"  - knowledge_id: {knowledge_id}",
                    "    version: 1.0.0",
                    f"    path: {relative_path}",
                    f"    content_sha256: {content_sha256}",
                ),
            ),
        )

    manifest_path = knowledge_root / "releases" / "manifests" / "fashion-knowledge-test.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        "\n".join(
            (
                "release_id: fashion-knowledge-test",
                "created_at: 2026-07-31",
                "approved_by: test-reviewer",
                "approval_scope: unit-test",
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
    return knowledge_root, manifest_path


def test_prepare_release_fragments_filters_unpublished_documents(
    tmp_path: Path,
) -> None:
    """验证只有 approved 且允许发布的知识会生成 RAG 片段。"""

    knowledge_root, manifest_path = _write_release(
        tmp_path,
        documents=(
            (
                "fk-draft-001",
                "knowledge/draft.md",
                "draft",
                True,
            ),
            (
                "fk-private-001",
                "knowledge/private.md",
                "approved",
                False,
            ),
        ),
    )

    # Loader 会先完成哈希与 Frontmatter 校验，再记录发布资格跳过结果。
    release = load_knowledge_release(
        knowledge_root=knowledge_root,
        manifest_path=manifest_path,
    )
    assert release.documents == ()
    assert len(release.skipped_documents) == 2

    prepared = prepare_release_fragments(
        release=release,
        text_splitter=TwoPartTextSplitter(),
    )

    assert prepared.fragments == ()


def test_prepare_release_fragments_builds_stable_ids_and_metadata(
    tmp_path: Path,
) -> None:
    """验证稳定片段 ID、章节内序号及 Chroma 元数据。"""

    knowledge_id = "fk-materials-linen-001"
    relative_path = "knowledge/01_materials/linen.md"
    knowledge_root, manifest_path = _write_release(
        tmp_path,
        documents=(
            (
                knowledge_id,
                relative_path,
                "approved",
                True,
            ),
        ),
    )
    release = load_knowledge_release(
        knowledge_root=knowledge_root,
        manifest_path=manifest_path,
    )

    prepared = prepare_release_fragments(
        release=release,
        text_splitter=TwoPartTextSplitter(),
    )

    fragment_ids = [fragment.metadata["fragment_id"] for fragment in prepared.fragments]
    assert fragment_ids == [
        f"{knowledge_id}::S01::001",
        f"{knowledge_id}::S01::002",
        f"{knowledge_id}::S02::001",
        f"{knowledge_id}::S02::002",
    ]

    # 每个片段都必须携带可追溯到知识源的完整元数据。
    for fragment in prepared.fragments:
        metadata = fragment.metadata
        assert metadata["fragment_id"] in fragment_ids
        assert metadata["knowledge_id"] == knowledge_id
        assert metadata["doc_type"] == "material_guide"
        assert metadata["version"] == "1.0.0"
        assert metadata["updated_at"] == "2026-07-31"
        assert metadata["source_ids"] == [
            "SRC-0001",
            "SRC-0002",
        ]
        assert metadata["source_path_or_url"] == relative_path
        assert metadata["title"] == "亚麻穿搭指南"
        assert metadata["tags"] == ["亚麻", "高温", "通勤"]
        assert fragment.page_content.startswith(
            "知识标题：亚麻穿搭指南\n"
            "知识类型：material_guide\n"
        )


def test_index_knowledge_release_writes_fragments_with_stable_ids(
    tmp_path: Path,
) -> None:
    """验证发布导入将准备好的片段及稳定 ID 一次写入向量库。"""

    knowledge_id = "fk-materials-linen-001"
    knowledge_root, manifest_path = _write_release(
        tmp_path,
        documents=(
            (
                knowledge_id,
                "knowledge/linen.md",
                "approved",
                True,
            ),
        ),
    )
    vector_store = Mock(spec=VectorStore)

    report = index_knowledge_release(
        knowledge_root=knowledge_root,
        manifest_path=manifest_path,
        text_splitter=TwoPartTextSplitter(),
        vector_store=vector_store,
    )

    vector_store.add_documents.assert_called_once()
    add_call = vector_store.add_documents.call_args
    written_fragments = add_call.args[0]
    written_ids = add_call.kwargs["ids"]

    assert len(written_fragments) == 4
    assert written_ids == [
        f"{knowledge_id}::S01::001",
        f"{knowledge_id}::S01::002",
        f"{knowledge_id}::S02::001",
        f"{knowledge_id}::S02::002",
    ]
    assert report.manifest_document_count == 1
    assert report.imported_document_count == 1
    assert report.skipped_document_count == 0
    assert report.fragment_count == 4


def test_index_knowledge_release_does_not_write_partial_release(
    tmp_path: Path,
) -> None:
    """验证任一文件校验失败时，整个发布都不会产生部分写入。"""

    knowledge_root, manifest_path = _write_release(
        tmp_path,
        documents=(
            (
                "fk-valid-001",
                "knowledge/valid.md",
                "approved",
                True,
            ),
            (
                "fk-corrupt-001",
                "knowledge/corrupt.md",
                "approved",
                True,
            ),
        ),
        corrupt_last_hash=True,
    )
    vector_store = Mock(spec=VectorStore)

    with pytest.raises(KnowledgeReleaseError):
        index_knowledge_release(
            knowledge_root=knowledge_root,
            manifest_path=manifest_path,
            text_splitter=TwoPartTextSplitter(),
            vector_store=vector_store,
        )

    vector_store.add_documents.assert_not_called()
