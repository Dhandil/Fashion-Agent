from pathlib import Path

from app.core.config import get_settings
from app.rag.loaders.text_splitter import create_text_splitter
from app.rag.releases.ingestion import (
    prepare_release_fragments,
    synchronize_prepared_release,
)
from app.rag.releases.loader import load_knowledge_release
from app.rag.vectorstores.provider import (
    get_knowledge_vector_store,
)


def main() -> None:
    """将通过正式 Manifest 发布的服装知识索引到持久化 Chroma。"""

    # 读取 RAG 配置
    settings = get_settings()

    # 创建配置化的文本切分器
    text_splitter = create_text_splitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    )

    # Manifest 路径相对独立知识库根目录，避免绑定某台机器的绝对路径
    knowledge_root = Path(
        settings.knowledge_repository_path,
    )
    manifest_path = (
        knowledge_root
        / settings.knowledge_release_manifest
    )

    # 在加载 Embedding 和打开 Chroma 前，先完成整批只读校验与切分
    release = load_knowledge_release(
        knowledge_root=knowledge_root,
        manifest_path=manifest_path,
    )
    prepared = prepare_release_fragments(
        release=release,
        text_splitter=text_splitter,
    )

    # 只有上面的整批校验成功后，才创建 Chroma 并执行实际写入
    vector_store = get_knowledge_vector_store()
    report = synchronize_prepared_release(
        prepared=prepared,
        vector_store=vector_store,
    )

    print(
        "知识入库完成："
        f"release={report.release_id}，"
        f"Manifest 文档={report.manifest_document_count}，"
        f"导入文档={report.imported_document_count}，"
        f"跳过文档={report.skipped_document_count}，"
        f"片段={report.fragment_count}，"
        f"清理旧片段={report.removed_fragment_count}。",
    )


if __name__ == "__main__":
    main()
