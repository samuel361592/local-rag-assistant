"""檢索、Context 格式化與模型回答協調。"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event
from typing import Any, Callable, Sequence

from langchain_core.documents import Document
from langchain_ollama import ChatOllama

from .config import Settings
from .retrieval_errors import (DegradableRetrievalError, KnowledgeStateError, DenseRetrievalError,
                               UserInputError, RetrievalError)
from .chunk_identity import validate_candidates
from .hybrid_retriever import ranked_documents, reciprocal_rank_fusion
from .source_location import build_location_label
from .document_loader import (
    CONTENT_TYPE_KEY,
    PAGE_NUMBER_KEY,
    SOURCE_FILENAME_KEY,
    VISUAL_CONTENT_TYPE,
)
from .prompt import INSUFFICIENT_INFORMATION_MESSAGE, SYSTEM_PROMPT, build_user_prompt
from .reranker import create_reranker, rerank_documents
from .vector_store import similarity_search


@dataclass(frozen=True, slots=True)
class SourceReference:
    number: int
    filename: str
    # Keep the original positional arguments compatible; new callers pass location_label.
    page_number: int | str | None = None
    content_type: str = "text"
    location_label: str = ""

    def __post_init__(self) -> None:
        if not self.location_label:
            object.__setattr__(self, "location_label", f"第 {self.page_number or '未知'} 頁")

    @property
    def content_type_label(self) -> str:
        return "視覺分析" if self.content_type == VISUAL_CONTENT_TYPE else "文件文字"

    @property
    def context_content_type_label(self) -> str:
        return (
            "VLM 視覺分析"
            if self.content_type == VISUAL_CONTENT_TYPE
            else "文件文字"
        )


@dataclass(frozen=True, slots=True)
class RagResult:
    answer: str
    sources: list[SourceReference]
    chunks: list[Document]
    degraded_components: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    retrieval_counts: dict = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RagProgressEvent:
    stage: str
    message: str
    detail: str = ""
    data: dict = field(default_factory=dict)


ProgressCallback = Callable[[RagProgressEvent], None]
TokenCallback = Callable[[str], None]
CancellationCallback = Callable[[], None]


class RagAnswerCancelled(Exception):
    """使用者取消回答，並保留取消前已產生的內容。"""

    def __init__(self, partial_result: RagResult) -> None:
        super().__init__("回答已由使用者停止。")
        self.partial_result = partial_result


def _source_details(document: Document, number: int) -> SourceReference:
    filename = str(
        document.metadata.get(SOURCE_FILENAME_KEY)
        or document.metadata.get("source")
        or "未知檔案"
    )
    page_number = document.metadata.get(PAGE_NUMBER_KEY, "未知")
    if document.metadata.get("source_type") == "excel":
        page_number = None
    content_type = str(document.metadata.get(CONTENT_TYPE_KEY, "text"))
    return SourceReference(number, filename, page_number, content_type, build_location_label(document.metadata))


def format_context(documents: Sequence[Document]) -> tuple[str, list[SourceReference]]:
    sections: list[str] = []
    sources: list[SourceReference] = []
    for number, document in enumerate(documents, start=1):
        source = _source_details(document, number)
        sources.append(source)
        sections.append(
            f"[來源 {number}]\n"
            f"檔名：{source.filename}\n"
            f"位置：{source.location_label}\n"
            f"內容類型：{source.context_content_type_label}\n"
            f"內容：{document.page_content.strip()}"
        )
    return "\n\n---\n\n".join(sections), sources


def _message_text(response: Any) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [item.get("text", "") if isinstance(item, dict) else str(item) for item in content]
        return "".join(parts).strip()
    return str(content).strip()


def _chunk_text(response: Any) -> str:
    """取出串流片段文字，保留片段前後空白以免拼接後文字黏在一起。"""

    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    return str(content)


def _emit_progress(
    progress_callback: ProgressCallback | None,
    stage: str,
    message: str,
    detail: str = "",
) -> None:
    if progress_callback is not None:
        progress_callback(RagProgressEvent(stage, message, detail))


class RagService:
    def __init__(
        self,
        vector_store: Any,
        settings: Settings,
        chat_model: Any | None = None,
        reranker: Any | None = None,
        bm25_store: Any | None = None,
        chunk_registry: dict | None = None,
    ) -> None:
        self.bm25_store = bm25_store
        self.chunk_registry = chunk_registry or {}
        self.degraded_components = []
        self.warnings = []
        self.retrieval_counts = {}
        self.vector_store = vector_store
        self.settings = settings
        self.reranker = reranker
        self.chat_model = chat_model or ChatOllama(
            model=settings.chat_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )

    def _retrieve_chunks(
        self, question, progress_callback=None, cancellation_callback=None,
    ):
        try:
            return self._retrieve_chunks_impl(question, progress_callback, cancellation_callback)
        except RagAnswerCancelled:
            raise
        except Exception as exc:
            self.retrieval_counts["final_chunk_count"] = None
            if self.retrieval_counts.get("reranker_status") is None:
                self.retrieval_counts["reranker_status"] = "not_run_upstream_failure"
            _emit_progress(progress_callback, "retrieval_failed", "檢索失敗，請稍後重試或重新建庫。")
            if isinstance(exc, RetrievalError):
                raise
            raise RetrievalError("檢索發生未預期錯誤。", cause=exc) from exc

    def _retrieve_chunks_impl(
        self,
        question: str,
        progress_callback: ProgressCallback | None = None,
        cancellation_callback: CancellationCallback | None = None,
    ) -> list[Document]:
        """執行一次 FAISS 搜尋，並視設定套用第二階段重排。"""

        def check_cancelled() -> None:
            if cancellation_callback is not None:
                cancellation_callback()

        self.degraded_components = []
        self.warnings = []
        counts = self.retrieval_counts = {k: None for k in (
            "dense_candidate_count", "bm25_candidate_count", "union_unique_count",
            "fused_candidate_count", "reranker_input_count", "reranker_output_count", "final_chunk_count")}
        hybrid = self.settings.hybrid_search_enabled
        if hybrid and (self.bm25_store is None or not self.chunk_registry):
            raise KnowledgeStateError("知識庫狀態不完整，請重新建庫。")
        def emit(stage, message, **data):
            if progress_callback is not None:
                progress_callback(RagProgressEvent(stage, message, data={**counts, **data}))
        def degraded(component):
            self.degraded_components.append(component)
            warning = f"{component} 暫時無法使用，已改用可用檢索排名。"
            self.warnings.append(warning)
            emit("retrieval_degraded", warning)
        dense, sparse, errors = [], [], []
        check_cancelled()
        emit("dense_retrieve", "正在執行 FAISS 語意檢索。")
        try:
            dense = similarity_search(self.vector_store, question, self.settings.retrieval_top_k)
            if self.chunk_registry:
                validate_candidates(dense, self.chunk_registry)
                dense = [r.document for r in ranked_documents(dense)]
            counts["dense_candidate_count"] = len(dense)
            counts["dense_status"] = "success" if dense else "success_empty"
            emit("dense_retrieved", f"語意檢索找到 {len(dense)} 筆候選。")
        except DenseRetrievalError as exc:
            errors.append(("dense", exc))
            counts["dense_status"] = "error"
            emit("dense_failed", "語意檢索失敗。")
        except Exception:
            counts["dense_status"] = "error"
            emit("dense_failed", "語意檢索無法完成。")
            raise
        check_cancelled()
        if hybrid:
            emit("sparse_retrieve", "正在執行 BM25 關鍵字檢索。")
            try:
                sparse = self.bm25_store.search(question, self.settings.bm25_top_k)
                validate_candidates([r.document for r in sparse], self.chunk_registry)
                counts["bm25_candidate_count"] = len(sparse)
                counts["bm25_status"] = ("empty_no_tokens" if self.bm25_store.status == "empty_no_tokens"
                                          else "success" if sparse else "success_empty")
                emit("sparse_retrieved", f"關鍵字檢索找到 {len(sparse)} 筆候選。")
            except DegradableRetrievalError as exc:
                errors.append(("bm25", exc))
                counts["bm25_status"] = "error"
                emit("sparse_failed", "關鍵字檢索失敗。")
            except Exception:
                counts["bm25_status"] = "error"
                emit("sparse_failed", "關鍵字檢索無法完成。")
                raise
        else:
            counts["bm25_status"] = "disabled"
            emit("hybrid_skipped", "Hybrid 已停用。", reason="disabled")
        if errors and not (dense or sparse):
            raise errors[0][1]
        for component, _ in errors:
            degraded(component)
        if hybrid:
            emit("fusion", "正在合併檢索排名。")
            counts["union_unique_count"] = len({d.metadata["chunk_id"] for d in dense} | {r.chunk_id for r in sparse})
            candidates = reciprocal_rank_fusion([ranked_documents(dense), sparse], self.settings.rrf_k, self.settings.fusion_top_k)
            candidates = [self.chunk_registry[d.metadata["chunk_id"]] for d in candidates]
            counts["fused_candidate_count"] = len(candidates)
            emit("fused", f"融合後有 {len(candidates)} 筆候選。")
        else:
            candidates = dense
        check_cancelled()
        chunks = candidates[:self.settings.top_k]
        if not self.settings.reranker_enabled:
            counts["reranker_status"] = "disabled"
            emit("rerank_skipped", "重排已停用。", reason="disabled")
        elif not candidates:
            counts["reranker_input_count"] = counts["reranker_output_count"] = 0
            counts["reranker_status"] = "success_empty"
            emit("rerank_skipped", "沒有候選，略過重排。", reason="no_candidates")
        else:
            emit("rerank", "正在重新排序候選資料。")
            counts["reranker_input_count"] = len(candidates)
            try:
                if self.reranker is None:
                    self.reranker = create_reranker(self.settings.reranker_model, self.settings.reranker_use_fp16,
                        device=self.settings.reranker_device, batch_size=self.settings.reranker_batch_size,
                        max_length=self.settings.reranker_max_length)
                chunks = rerank_documents(question, candidates, self.reranker, self.settings.top_k)
                counts["reranker_output_count"] = len(candidates)
                counts["reranker_status"] = "success"
                _emit_progress(progress_callback, "reranked", f"重排完成，選出 {len(chunks)} 筆。", "\n".join(_source_details(d, i).location_label for i, d in enumerate(chunks, 1)))
            except DegradableRetrievalError:
                counts["reranker_status"] = "error"
                emit("rerank_failed", "重排失敗。")
                degraded("reranker")
            except Exception:
                counts["reranker_status"] = "error"
                emit("rerank_failed", "重排無法完成。")
                raise
        check_cancelled()
        counts["final_chunk_count"] = len(chunks)
        return chunks

    def answer(
        self,
        question: str,
        progress_callback: ProgressCallback | None = None,
    ) -> RagResult:
        clean_question = question.strip()
        if not clean_question:
            raise UserInputError("請先輸入問題。")

        _emit_progress(progress_callback, "received", "已收到問題。", clean_question)
        chunks = self._retrieve_chunks(clean_question, progress_callback)
        if not chunks:
            _emit_progress(
                progress_callback,
                "no_results",
                "沒有檢索到可用文字區塊。",
            )
            return RagResult(INSUFFICIENT_INFORMATION_MESSAGE, [], [], list(self.degraded_components), list(self.warnings), dict(self.retrieval_counts))

        _emit_progress(
            progress_callback,
            "context",
            "正在組合帶來源編號的 Context。",
        )
        context, sources = format_context(chunks)
        _emit_progress(
            progress_callback,
            "generate",
            f"正在呼叫 {self.settings.chat_model} 產生回答。",
        )
        response = self.chat_model.invoke(
            [
                ("system", SYSTEM_PROMPT),
                ("human", build_user_prompt(clean_question, context)),
            ]
        )
        answer = _message_text(response) or INSUFFICIENT_INFORMATION_MESSAGE
        _emit_progress(progress_callback, "complete", "回答產生完成。")
        return RagResult(answer, sources, chunks, list(self.degraded_components), list(self.warnings), dict(self.retrieval_counts))

    def answer_stream(
        self,
        question: str,
        *,
        cancel_event: Event,
        progress_callback: ProgressCallback | None = None,
        token_callback: TokenCallback | None = None,
    ) -> RagResult:
        """以串流方式回答問題，並在安全檢查點回應取消要求。"""

        clean_question = question.strip()
        if not clean_question:
            raise UserInputError("請先輸入問題。")

        chunks: list[Document] = []
        sources: list[SourceReference] = []
        answer_parts: list[str] = []

        def raise_if_cancelled() -> None:
            if not cancel_event.is_set():
                return
            partial_answer = "".join(answer_parts).strip()
            _emit_progress(progress_callback, "cancelled", "回答已由使用者停止。")
            raise RagAnswerCancelled(
                RagResult(partial_answer, list(sources), list(chunks), list(self.degraded_components),
                          list(self.warnings), dict(self.retrieval_counts))
            )

        raise_if_cancelled()
        _emit_progress(progress_callback, "received", "已收到問題。", clean_question)
        chunks = self._retrieve_chunks(
            clean_question,
            progress_callback,
            raise_if_cancelled,
        )
        if not chunks:
            _emit_progress(
                progress_callback,
                "no_results",
                "沒有檢索到可用文字區塊。",
            )
            return RagResult(INSUFFICIENT_INFORMATION_MESSAGE, [], [], list(self.degraded_components), list(self.warnings), dict(self.retrieval_counts))

        raise_if_cancelled()
        _emit_progress(
            progress_callback,
            "context",
            "正在組合帶來源編號的 Context。",
        )
        context, sources = format_context(chunks)
        raise_if_cancelled()
        _emit_progress(
            progress_callback,
            "generate",
            f"正在呼叫 {self.settings.chat_model} 產生回答。",
        )

        response_stream = self.chat_model.stream(
            [
                ("system", SYSTEM_PROMPT),
                ("human", build_user_prompt(clean_question, context)),
            ]
        )
        try:
            for response_chunk in response_stream:
                raise_if_cancelled()
                text = _chunk_text(response_chunk)
                if not text:
                    continue
                answer_parts.append(text)
                if token_callback is not None:
                    token_callback(text)
            raise_if_cancelled()
        finally:
            close_stream = getattr(response_stream, "close", None)
            if callable(close_stream):
                close_stream()

        answer = "".join(answer_parts).strip() or INSUFFICIENT_INFORMATION_MESSAGE
        _emit_progress(progress_callback, "complete", "回答產生完成。")
        return RagResult(answer, sources, chunks, list(self.degraded_components), list(self.warnings), dict(self.retrieval_counts))
