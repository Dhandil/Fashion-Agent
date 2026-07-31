from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.rag.releases.exceptions import KnowledgeReleaseError
from app.rag.releases.loader import load_knowledge_release


def _build_knowledge_document(
    *,
    knowledge_id: str = "fk-materials-linen-001",
    status: str = "approved",
    publish_to_rag: bool = True,
) -> str:
    """生成一份带 Frontmatter 和稳定章节编号的测试知识。"""

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
---

# 亚麻穿搭指南

## S01 适用场景

亚麻面料适合炎热天气。

## S02 穿着提醒

亚麻容易产生自然褶皱。
"""


def _write_manifest(
    *,
    knowledge_root: Path,
    document_path: str,
    content_sha256: str,
    knowledge_id: str = "fk-materials-linen-001",
) -> Path:
    """写入仅包含一项知识白名单的 Manifest。"""

    manifest_path = knowledge_root / "releases" / "manifests" / "fashion-knowledge-test.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        f"""release_id: fashion-knowledge-test
created_at: 2026-07-31
approved_by: test-reviewer
approval_scope: unit-test
target: fashion-agent-chroma
supersedes:
batch: TEST-BATCH
documents:
  - knowledge_id: {knowledge_id}
    version: 1.0.0
    path: {document_path}
    content_sha256: {content_sha256}
""",
        encoding="utf-8",
    )
    return manifest_path


def test_load_knowledge_release_only_reads_manifest_whitelist(
    tmp_path: Path,
) -> None:
    """验证 Loader 不会递归扫描 Manifest 未列出的文件或禁用目录。"""

    knowledge_root = tmp_path / "Fashion-Agent-Knowledge"
    listed_path = knowledge_root / "knowledge" / "01_materials" / "linen.md"
    listed_path.parent.mkdir(parents=True)
    listed_path.write_text(
        _build_knowledge_document(),
        encoding="utf-8",
    )

    # 这些文件故意不包含合法 Frontmatter。
    # 如果 Loader 错误地扫描目录，测试就会失败。
    extra_paths = (
        knowledge_root / "knowledge" / "unlisted.md",
        knowledge_root / "sources" / "source.md",
        knowledge_root / "staging" / "draft.md",
        knowledge_root / "archive" / "old.md",
        knowledge_root / "evaluation" / "case.md",
    )
    for extra_path in extra_paths:
        extra_path.parent.mkdir(parents=True, exist_ok=True)
        extra_path.write_text(
            "这不是 Manifest 白名单中的知识。",
            encoding="utf-8",
        )

    expected_sha256 = hashlib.sha256(
        listed_path.read_bytes(),
    ).hexdigest()
    manifest_path = _write_manifest(
        knowledge_root=knowledge_root,
        document_path="knowledge/01_materials/linen.md",
        content_sha256=expected_sha256,
    )

    release = load_knowledge_release(
        knowledge_root=knowledge_root,
        manifest_path=manifest_path,
    )

    # 只有 Manifest 明确列出的 linen.md 被加载。
    assert len(release.documents) == 1

    document = release.documents[0]
    assert document.frontmatter.knowledge_id == "fk-materials-linen-001"
    assert document.frontmatter.doc_type == "material_guide"
    assert document.frontmatter.status == "approved"
    assert document.frontmatter.runtime.publish_to_rag is True
    assert document.frontmatter.source_ids == (
        "SRC-0001",
        "SRC-0002",
    )
    assert document.source_path_or_url == ("knowledge/01_materials/linen.md")

    # Frontmatter 之外的正文应按稳定章节编号解析。
    assert tuple(section.section_id for section in document.sections) == ("S01", "S02")


def test_load_knowledge_release_rejects_sha256_mismatch(
    tmp_path: Path,
) -> None:
    """验证知识文件内容与 Manifest 哈希不一致时拒绝导入。"""

    knowledge_root = tmp_path / "Fashion-Agent-Knowledge"
    document_path = knowledge_root / "knowledge" / "linen.md"
    document_path.parent.mkdir(parents=True)
    document_path.write_text(
        _build_knowledge_document(),
        encoding="utf-8",
    )
    manifest_path = _write_manifest(
        knowledge_root=knowledge_root,
        document_path="knowledge/linen.md",
        content_sha256="0" * 64,
    )

    with pytest.raises(KnowledgeReleaseError):
        load_knowledge_release(
            knowledge_root=knowledge_root,
            manifest_path=manifest_path,
        )


@pytest.mark.parametrize(
    "forbidden_path",
    (
        "../outside.md",
        "sources/source.md",
        "staging/draft.md",
        "archive/old.md",
        "evaluation/case.md",
    ),
)
def test_load_knowledge_release_rejects_forbidden_paths(
    tmp_path: Path,
    forbidden_path: str,
) -> None:
    """验证路径逃逸和明确禁用目录不能进入知识发布。"""

    knowledge_root = tmp_path / "Fashion-Agent-Knowledge"
    knowledge_root.mkdir()
    manifest_path = _write_manifest(
        knowledge_root=knowledge_root,
        document_path=forbidden_path,
        content_sha256="0" * 64,
    )

    with pytest.raises(KnowledgeReleaseError):
        load_knowledge_release(
            knowledge_root=knowledge_root,
            manifest_path=manifest_path,
        )
