from dataclasses import dataclass
from datetime import date

from langchain_core.documents import Document
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.rag.releases.exceptions import KnowledgeManifestError


class ManifestDocument(BaseModel):
    """Manifest 中一篇知识文档的不可变声明。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    knowledge_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    path: str = Field(min_length=1)
    content_sha256: str = Field(
        pattern=r"^[0-9a-f]{64}$",
    )


class KnowledgeReleaseManifest(BaseModel):
    """独立知识库的一次受治理发布。"""

    model_config = ConfigDict(extra="forbid", frozen=True)

    release_id: str = Field(min_length=1)
    created_at: date
    approved_by: str = Field(min_length=1)
    approval_scope: str = Field(min_length=1)
    target: str = Field(min_length=1)
    supersedes: str | None = None
    batch: str = Field(min_length=1)
    documents: tuple[ManifestDocument, ...] = Field(
        min_length=1,
    )

    @model_validator(mode="after")
    def validate_unique_documents(
        self,
    ) -> "KnowledgeReleaseManifest":
        """禁止同一 Manifest 重复声明知识 ID 或文件路径。"""

        knowledge_ids = [
            document.knowledge_id for document in self.documents
        ]
        paths = [
            document.path for document in self.documents
        ]

        if len(knowledge_ids) != len(set(knowledge_ids)):
            raise KnowledgeManifestError(
                "Manifest 中存在重复的 knowledge_id。",
            )

        if len(paths) != len(set(paths)):
            raise KnowledgeManifestError(
                "Manifest 中存在重复的文档路径。",
            )

        return self


class KnowledgeRuntime(BaseModel):
    """知识文档在运行时的发布开关。"""

    model_config = ConfigDict(extra="ignore", frozen=True)

    publish_to_rag: bool = False


class KnowledgeFrontmatter(BaseModel):
    """RAG 导入所需的最小 Frontmatter 字段集合。"""

    model_config = ConfigDict(extra="ignore", frozen=True)

    knowledge_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    doc_type: str = Field(min_length=1)
    status: str = Field(min_length=1)
    version: str = Field(min_length=1)
    updated_at: date
    source_ids: tuple[str, ...] = Field(min_length=1)
    runtime: KnowledgeRuntime
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class KnowledgeSection:
    """从 Markdown H2 中解析出的稳定知识章节。"""

    section_id: str
    content: str


@dataclass(frozen=True, slots=True)
class LoadedKnowledgeDocument:
    """已经通过完整性和发布条件校验的知识文档。"""

    frontmatter: KnowledgeFrontmatter
    source_path_or_url: str
    sections: tuple[KnowledgeSection, ...]


@dataclass(frozen=True, slots=True)
class SkippedKnowledgeDocument:
    """存在于 Manifest 中、但未获准进入 RAG 的知识文档。"""

    knowledge_id: str
    source_path_or_url: str
    reason: str


@dataclass(frozen=True, slots=True)
class LoadedKnowledgeRelease:
    """完成 Manifest、SHA 和文档结构校验的知识发布。"""

    manifest: KnowledgeReleaseManifest
    documents: tuple[LoadedKnowledgeDocument, ...]
    skipped_documents: tuple[SkippedKnowledgeDocument, ...]


@dataclass(frozen=True, slots=True)
class PreparedKnowledgeRelease:
    """已经切分、但尚未写入向量库的知识发布。"""

    release: LoadedKnowledgeRelease
    fragments: tuple[Document, ...]
    fragment_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class KnowledgeImportReport:
    """一次 Manifest 知识入库的结果摘要。"""

    release_id: str
    manifest_document_count: int
    imported_document_count: int
    skipped_document_count: int
    fragment_count: int
    removed_fragment_count: int = 0
