from dataclasses import replace
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_text_splitters.base import TextSplitter

from app.rag.releases.exceptions import KnowledgeDocumentError
from app.rag.releases.loader import load_knowledge_release
from app.rag.releases.models import (
    KnowledgeImportReport,
    LoadedKnowledgeRelease,
    PreparedKnowledgeRelease,
)


def prepare_release_fragments(
    release: LoadedKnowledgeRelease,
    text_splitter: TextSplitter,
) -> PreparedKnowledgeRelease:
    """先完成全部稳定切分和元数据构造，但暂不写入 Chroma。"""

    fragments: list[Document] = []
    fragment_ids: list[str] = []

    for knowledge_document in release.documents:
        frontmatter = knowledge_document.frontmatter

        for section in knowledge_document.sections:
            split_contents = text_splitter.split_text(
                section.content,
            )

            for split_sequence, content in enumerate(
                split_contents,
                start=1,
            ):
                # 三位序号来自知识库治理约定，并在每个稳定章节内重新计数。
                fragment_id = (
                    f"{frontmatter.knowledge_id}::"
                    f"{section.section_id}::"
                    f"{split_sequence:03d}"
                )

                metadata: dict[str, object] = {
                    "fragment_id": fragment_id,
                    "knowledge_id": frontmatter.knowledge_id,
                    "doc_type": frontmatter.doc_type,
                    "version": frontmatter.version,
                    "updated_at": frontmatter.updated_at.isoformat(),
                    "source_ids": list(frontmatter.source_ids),
                    "source_path_or_url": (
                        knowledge_document.source_path_or_url
                    ),
                    # 额外保留章节与发布身份，便于过滤、审计和问题定位。
                    "section_id": section.section_id,
                    "release_id": release.manifest.release_id,
                    "title": frontmatter.title,
                }
                if frontmatter.tags:
                    metadata["tags"] = list(frontmatter.tags)

                # 二次切分后的片段可能只剩表格或代码块，因此每段都补充稳定语境。
                context_lines = [
                    f"知识标题：{frontmatter.title}",
                    f"知识类型：{frontmatter.doc_type}",
                    f"稳定章节：{section.section_id}",
                ]
                if frontmatter.tags:
                    context_lines.append(
                        "知识标签："
                        + "、".join(frontmatter.tags),
                    )
                contextual_content = (
                    "\n".join(context_lines)
                    + "\n\n"
                    + content
                )
                fragments.append(
                    Document(
                        page_content=contextual_content,
                        metadata=metadata,
                    ),
                )
                fragment_ids.append(fragment_id)

    if len(fragment_ids) != len(set(fragment_ids)):
        raise KnowledgeDocumentError(
            "知识发布生成了重复的 fragment_id。",
        )

    return PreparedKnowledgeRelease(
        release=release,
        fragments=tuple(fragments),
        fragment_ids=tuple(fragment_ids),
    )


def index_knowledge_release(
    *,
    knowledge_root: Path,
    manifest_path: Path,
    text_splitter: TextSplitter,
    vector_store: VectorStore,
) -> KnowledgeImportReport:
    """整批验证和切分成功后，将受治理知识一次写入向量库。"""

    release = load_knowledge_release(
        knowledge_root=knowledge_root,
        manifest_path=manifest_path,
    )
    prepared = prepare_release_fragments(
        release=release,
        text_splitter=text_splitter,
    )

    return write_prepared_release(
        prepared=prepared,
        vector_store=vector_store,
    )


def write_prepared_release(
    *,
    prepared: PreparedKnowledgeRelease,
    vector_store: VectorStore,
) -> KnowledgeImportReport:
    """把已经整批验证成功的知识片段写入向量库。"""

    # 只有整批 Manifest、SHA、Frontmatter 和章节全部通过后才执行写入。
    if prepared.fragments:
        vector_store.add_documents(
            list(prepared.fragments),
            ids=list(prepared.fragment_ids),
        )

    release = prepared.release
    return KnowledgeImportReport(
        release_id=release.manifest.release_id,
        manifest_document_count=len(
            release.manifest.documents,
        ),
        imported_document_count=len(release.documents),
        skipped_document_count=len(
            release.skipped_documents,
        ),
        fragment_count=len(prepared.fragments),
    )


def synchronize_prepared_release(
    *,
    prepared: PreparedKnowledgeRelease,
    vector_store: Chroma,
) -> KnowledgeImportReport:
    """写入正式发布，并清理集合中不属于该 Manifest 的旧片段。"""

    if not prepared.fragments:
        raise KnowledgeDocumentError(
            "正式知识发布没有可写入的已批准片段，拒绝清空现有集合。",
        )

    # 先完成新片段 upsert；Embedding 或写入失败时不会主动删除旧知识。
    report = write_prepared_release(
        prepared=prepared,
        vector_store=vector_store,
    )

    stored_result = vector_store.get(include=[])
    stored_ids = {
        str(stored_id)
        for stored_id in stored_result.get("ids", [])
    }
    expected_ids = set(prepared.fragment_ids)
    stale_ids = sorted(stored_ids - expected_ids)

    # 该 Chroma collection 专门保存正式服装知识，因此移除旧发布和示例片段。
    if stale_ids:
        vector_store.delete(ids=stale_ids)

    return replace(
        report,
        removed_fragment_count=len(stale_ids),
    )
