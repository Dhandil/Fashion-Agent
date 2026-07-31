import re
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path, PurePosixPath
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from app.rag.releases.exceptions import (
    KnowledgeDocumentError,
    KnowledgeIntegrityError,
    KnowledgeManifestError,
    KnowledgeReleaseError,
)
from app.rag.releases.models import (
    KnowledgeFrontmatter,
    KnowledgeReleaseManifest,
    KnowledgeSection,
    LoadedKnowledgeDocument,
    LoadedKnowledgeRelease,
    ManifestDocument,
    SkippedKnowledgeDocument,
)

# Manifest 只能引用正式 knowledge 目录，以下工作区绝不能进入 RAG。
_EXCLUDED_DIRECTORIES = {
    "sources",
    "staging",
    "archive",
    "evaluation",
}

# 只把二级标题 S01、S02 等视为稳定章节；S03.1 等三级标题属于父章节。
_STABLE_SECTION_PATTERN = re.compile(
    r"^##[ \t]+(?P<section_id>S\d{2})(?:[ \t]+.*)?$",
    flags=re.MULTILINE,
)
_ANY_H2_PATTERN = re.compile(
    r"^##(?!#)(?:[ \t]+.*)?$",
    flags=re.MULTILINE,
)


def _load_yaml_mapping(
    content: str,
    *,
    description: str,
) -> dict[str, Any]:
    """安全解析 YAML，并确保顶层结构是映射。"""

    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise KnowledgeManifestError(
            f"{description} 不是合法 YAML。",
        ) from exc

    if not isinstance(parsed, dict):
        raise KnowledgeManifestError(
            f"{description} 顶层必须是 YAML 映射。",
        )

    return parsed


def _resolve_manifest_document(
    knowledge_root: Path,
    manifest_document: ManifestDocument,
) -> tuple[Path, str]:
    """把 Manifest 相对路径解析到受控 knowledge 目录。"""

    relative_path = manifest_document.path
    pure_path = PurePosixPath(relative_path)

    if (
        pure_path.is_absolute()
        or "\\" in relative_path
        or ".." in pure_path.parts
        or pure_path.suffix.lower() != ".md"
    ):
        raise KnowledgeManifestError(
            f"Manifest 文档路径不合法：{relative_path}",
        )

    lowered_parts = {
        part.lower() for part in pure_path.parts
    }
    if lowered_parts & _EXCLUDED_DIRECTORIES:
        raise KnowledgeManifestError(
            f"Manifest 禁止引用非发布目录：{relative_path}",
        )

    if not pure_path.parts or pure_path.parts[0].lower() != "knowledge":
        raise KnowledgeManifestError(
            f"Manifest 只能引用 knowledge/ 下的文档：{relative_path}",
        )

    resolved_root = knowledge_root.resolve()
    resolved_knowledge_directory = (
        resolved_root / "knowledge"
    ).resolve()
    resolved_document = (
        resolved_root / Path(*pure_path.parts)
    ).resolve()

    if not resolved_document.is_relative_to(
        resolved_knowledge_directory,
    ):
        raise KnowledgeManifestError(
            f"Manifest 文档路径逃逸 knowledge/：{relative_path}",
        )

    if not resolved_document.is_file():
        raise KnowledgeManifestError(
            f"Manifest 文档不存在：{relative_path}",
        )

    # PurePosixPath 统一不同操作系统上的来源格式，避免写入 Windows 绝对路径。
    normalized_source = pure_path.as_posix()
    return resolved_document, normalized_source


def _verify_sha256(
    content: bytes,
    manifest_document: ManifestDocument,
) -> None:
    """在解码和换行处理前校验原始文件字节。"""

    actual_sha256 = sha256(content).hexdigest()
    if not compare_digest(
        actual_sha256,
        manifest_document.content_sha256,
    ):
        raise KnowledgeIntegrityError(
            "知识文档 SHA-256 校验失败："
            f"{manifest_document.path}",
        )


def _parse_frontmatter_and_body(
    content: bytes,
    *,
    source_path: str,
) -> tuple[KnowledgeFrontmatter, str]:
    """解析 Markdown 开头的 YAML Frontmatter 和正文。"""

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise KnowledgeDocumentError(
            f"知识文档必须使用 UTF-8 编码：{source_path}",
        ) from exc

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise KnowledgeDocumentError(
            f"知识文档缺少起始 Frontmatter：{source_path}",
        )

    closing_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == "---"
        ),
        None,
    )
    if closing_index is None:
        raise KnowledgeDocumentError(
            f"知识文档缺少 Frontmatter 结束标记：{source_path}",
        )

    frontmatter_text = "\n".join(lines[1:closing_index])
    body = "\n".join(lines[closing_index + 1 :]).strip()

    try:
        frontmatter_data = _load_yaml_mapping(
            frontmatter_text,
            description=f"Frontmatter（{source_path}）",
        )
        frontmatter = KnowledgeFrontmatter.model_validate(
            frontmatter_data,
        )
    except (ValidationError, KnowledgeManifestError) as exc:
        raise KnowledgeDocumentError(
            f"知识文档 Frontmatter 校验失败：{source_path}",
        ) from exc

    return frontmatter, body


def _parse_stable_sections(
    body: str,
    *,
    source_path: str,
) -> tuple[KnowledgeSection, ...]:
    """按稳定 H2 编号切分正文，同时保留章节内的 H3、表格和代码块。"""

    matches = list(_STABLE_SECTION_PATTERN.finditer(body))
    all_h2_matches = list(_ANY_H2_PATTERN.finditer(body))

    if not matches:
        raise KnowledgeDocumentError(
            f"知识文档没有 S01、S02 等稳定章节：{source_path}",
        )

    if len(matches) != len(all_h2_matches):
        raise KnowledgeDocumentError(
            f"知识文档存在未编号的 H2 章节：{source_path}",
        )

    actual_section_ids = [
        match.group("section_id") for match in matches
    ]
    expected_section_ids = [
        f"S{sequence:02d}"
        for sequence in range(1, len(matches) + 1)
    ]
    if actual_section_ids != expected_section_ids:
        raise KnowledgeDocumentError(
            f"知识文档稳定章节必须从 S01 连续编号：{source_path}",
        )

    sections: list[KnowledgeSection] = []
    for index, match in enumerate(matches):
        next_start = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(body)
        )
        section_content = body[match.start() : next_start].strip()
        sections.append(
            KnowledgeSection(
                section_id=match.group("section_id"),
                content=section_content,
            ),
        )

    return tuple(sections)


def _load_manifest(
    manifest_path: Path,
) -> KnowledgeReleaseManifest:
    """读取并校验发布 Manifest 自身。"""

    if not manifest_path.is_file():
        raise KnowledgeManifestError(
            f"知识发布 Manifest 不存在：{manifest_path}",
        )

    try:
        manifest_text = manifest_path.read_text(
            encoding="utf-8",
        )
    except UnicodeDecodeError as exc:
        raise KnowledgeManifestError(
            "知识发布 Manifest 必须使用 UTF-8 编码。",
        ) from exc

    manifest_data = _load_yaml_mapping(
        manifest_text,
        description="知识发布 Manifest",
    )

    try:
        return KnowledgeReleaseManifest.model_validate(
            manifest_data,
        )
    except (ValidationError, KnowledgeReleaseError) as exc:
        raise KnowledgeManifestError(
            "知识发布 Manifest 字段校验失败。",
        ) from exc


def load_knowledge_release(
    knowledge_root: Path,
    manifest_path: Path,
) -> LoadedKnowledgeRelease:
    """按 Manifest 白名单加载并验证一次完整知识发布。"""

    manifest = _load_manifest(manifest_path)
    loaded_documents: list[LoadedKnowledgeDocument] = []
    skipped_documents: list[SkippedKnowledgeDocument] = []

    # 不扫描 knowledge_root；输入范围严格等于 Manifest documents。
    for manifest_document in manifest.documents:
        document_path, source_path = _resolve_manifest_document(
            knowledge_root,
            manifest_document,
        )
        raw_content = document_path.read_bytes()

        # 每篇文档先校验原始字节 SHA，再解析 Frontmatter 和正文。
        _verify_sha256(raw_content, manifest_document)
        frontmatter, body = _parse_frontmatter_and_body(
            raw_content,
            source_path=source_path,
        )

        if frontmatter.knowledge_id != manifest_document.knowledge_id:
            raise KnowledgeDocumentError(
                "Manifest 与 Frontmatter 的 knowledge_id 不一致："
                f"{source_path}",
            )

        if frontmatter.version != manifest_document.version:
            raise KnowledgeDocumentError(
                "Manifest 与 Frontmatter 的 version 不一致："
                f"{source_path}",
            )

        if (
            frontmatter.status != "approved"
            or frontmatter.runtime.publish_to_rag is not True
        ):
            skipped_documents.append(
                SkippedKnowledgeDocument(
                    knowledge_id=frontmatter.knowledge_id,
                    source_path_or_url=source_path,
                    reason=(
                        "仅 status=approved 且 "
                        "runtime.publish_to_rag=true 的知识可进入 RAG"
                    ),
                ),
            )
            continue

        sections = _parse_stable_sections(
            body,
            source_path=source_path,
        )
        loaded_documents.append(
            LoadedKnowledgeDocument(
                frontmatter=frontmatter,
                source_path_or_url=source_path,
                sections=sections,
            ),
        )

    return LoadedKnowledgeRelease(
        manifest=manifest,
        documents=tuple(loaded_documents),
        skipped_documents=tuple(skipped_documents),
    )
