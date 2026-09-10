"""Commit a fully built knowledge base without retaining stale answer state."""

from typing import MutableMapping, Any, Sequence

from .config import Settings
from .chunk_identity import build_registry, validate_candidates
from .retrieval_errors import KnowledgeStateError
from .document_loader import DocumentBatch
from .release_policy import runtime_verification_status


def commit_knowledge_base(
    state: MutableMapping[str, Any], batch: DocumentBatch, vector_store: Any,
    filenames: Sequence[str], settings: Settings,
) -> None:
    registry = build_registry(batch.chunks)
    if hasattr(vector_store, "index_to_docstore_id"):
        indexed = [vector_store.docstore.search(key) for key in vector_store.index_to_docstore_id.values()]
        if len(indexed) != len(registry):
            raise KnowledgeStateError("向量索引與 Chunk Registry 數量不同。")
        validate_candidates(indexed, registry)
    bm25 = None
    if settings.hybrid_search_enabled:
        if len(registry) != len(batch.chunks):
            raise KnowledgeStateError("知識庫缺少 Chunk ID。")
        from .bm25_store import BM25Store
        bm25 = BM25Store.from_documents(batch.chunks, k1=settings.bm25_k1, b=settings.bm25_b, epsilon=settings.bm25_epsilon)
    stats = batch.extraction_stats
    metrics = {
        "hybrid_verification_status": runtime_verification_status(settings),
        "documents": batch.document_count, "pages": batch.page_count,
        "chunks": len(batch.chunks), "native_pages": stats.native_page_count,
        "ocr_pages": stats.ocr_page_count, "image_pages": stats.image_page_count,
        "average_ocr_confidence": stats.average_ocr_confidence,
        "vlm_pages": stats.vlm_page_count, "vlm_failures": stats.vlm_failure_count,
        "visual_chunks": stats.visual_chunk_count, "vlm_model": settings.vlm_model,
        **{name: getattr(stats, name) for name in stats.__dataclass_fields__ if name.startswith("excel_")},
    }
    replacement = {
        "vector_store": vector_store, "knowledge_stats": metrics,
        "knowledge_chunks": batch.chunks, "parsed_text_by_source": batch.parsed_text_by_source,
        "ocr_text_by_source": batch.ocr_text_by_source,
        "visual_text_by_source": batch.visual_text_by_source,
        "vlm_failures_by_source": batch.vlm_failures_by_source,
        "active_knowledge_files": list(filenames), "chunk_preview_page": 1,
    }
    replacement["chunk_registry"] = registry
    metrics.update(bm25_source_document_count=None, bm25_searchable_document_count=None,
                   bm25_excluded_empty_token_count=None, bm25_status="disabled")
    if bm25 is not None:
        replacement["bm25_store"] = bm25
        metrics.update(bm25_source_document_count=bm25.source_document_count,
                       bm25_searchable_document_count=bm25.searchable_document_count,
                       bm25_excluded_empty_token_count=bm25.source_document_count-bm25.searchable_document_count,
                       bm25_status=bm25.status)
    transactional_commit(state, replacement)


QUERY_BOUND_STATE_KEYS = (
        "chunk_preview_filename", "chunk_preview_page_filter", "chunk_preview_search",
        "chunk_preview_source_type", "chunk_preview_sheet", "ocr_preview_source",
        "vlm_preview_source", "rag_result", "rag_progress_events", "rag_job",
        "messages", "chat_history", "chat_messages",
    "retrieval_counts", "retrieval_warnings", "last_answer", "source_filter",
)
KB_BOUND_STATE_KEYS = ("vector_store", "bm25_store", "chunk_registry", "knowledge_stats",
    "knowledge_chunks", "parsed_text_by_source", "ocr_text_by_source", "visual_text_by_source",
    "vlm_failures_by_source", "active_knowledge_files", "chunk_preview_page")


def transactional_commit(state, replacement):
    keys = set(KB_BOUND_STATE_KEYS) | set(QUERY_BOUND_STATE_KEYS) | set(replacement)
    old = {key: state[key] for key in keys if key in state}
    try:
        for key in keys:
            if key in replacement:
                state[key] = replacement[key]
            else:
                state.pop(key, None)
    except Exception as exc:
        for key in keys:
            if key in old:
                state[key] = old[key]
            else:
                state.pop(key, None)
        raise KnowledgeStateError("知識庫提交失敗，已保留舊知識庫。", cause=exc) from exc
