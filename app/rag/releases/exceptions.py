from app.core.exceptions import FashionAgentError


class KnowledgeReleaseError(FashionAgentError):
    """知识发布清单或知识文档不符合导入约束。"""


class KnowledgeManifestError(KnowledgeReleaseError):
    """知识发布清单格式、路径或唯一性校验失败。"""


class KnowledgeIntegrityError(KnowledgeReleaseError):
    """知识文档的实际内容与 Manifest 中的 SHA-256 不一致。"""


class KnowledgeDocumentError(KnowledgeReleaseError):
    """知识文档的 Frontmatter、身份或稳定章节不合法。"""
