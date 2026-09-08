"""Commit a fully built knowledge base without retaining stale answer state."""

from typing import MutableMapping, Any, Sequence

from .config import Settings
from .document_loader import DocumentBatch


def commit_knowledge_base(
    state: MutableMapping[str, Any], batch: DocumentBatch, vector_store: Any,
    filenames: Sequence[str], settings: Settings,
) -> None:
    stats = batch.extraction_stats
    metrics = {
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
    state.update(replacement)
    for key in (
        "chunk_preview_filename", "chunk_preview_page_filter", "chunk_preview_search",
        "chunk_preview_source_type", "chunk_preview_sheet", "ocr_preview_source",
        "vlm_preview_source", "rag_result", "rag_progress_events", "rag_job",
        "messages", "chat_history", "chat_messages",
    ):
        state.pop(key, None)
