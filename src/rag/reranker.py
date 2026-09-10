"""以 FlagEmbedding 對第一階段檢索結果重新評分與排序。"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from math import isfinite
from numbers import Real
from typing import Any
from pathlib import Path
from hashlib import sha256
import httpx
from .retrieval_errors import RerankerOperationalError, RerankerOutputError, RerankerIntegrityError

RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
RERANKER_WEIGHTS_SHA256 = "d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286"

from langchain_core.documents import Document


class RerankerError(RerankerOperationalError):
    """Reranker 載入或計算失敗。"""


class RerankerDependencyError(RerankerError):
    """缺少 FlagEmbedding 相依套件。"""


class RerankerDownloadError(RerankerError):
    """無法從 Hugging Face 下載模型。"""


class RerankerModelNotFoundError(RerankerIntegrityError):
    """指定的 Hugging Face 模型不存在或無法存取。"""


class RerankerLoadError(RerankerError):
    """模型存在但無法載入。"""


class RerankerComputeError(RerankerError):
    """模型評分失敗。"""


class RerankerMemoryError(RerankerError):
    """載入模型或評分時記憶體不足。"""


def _error_detail(error: BaseException) -> str:
    return str(error).strip() or type(error).__name__


def _is_memory_error(error: BaseException) -> bool:
    detail = _error_detail(error).casefold()
    return isinstance(error, MemoryError) or any(
        marker in detail
        for marker in ("out of memory", "cannot allocate memory", "bad allocation")
    )


@lru_cache(maxsize=None)
def create_reranker(model_name: str, use_fp16: bool, *, device: str | None = None,
                    batch_size: int = 128, max_length: int = 512) -> Any:
    """延遲載入並快取 FlagReranker；不在模組 import 時載入模型。"""

    clean_model_name = model_name.strip()
    if not clean_model_name:
        raise ValueError("RERANKER_MODEL 不可為空白。")

    try:
        from FlagEmbedding import FlagReranker
    except (ImportError, ModuleNotFoundError) as exc:
        raise RerankerDependencyError(
            "未安裝 FlagEmbedding，無法建立 Reranker。"
        ) from exc

    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import LocalEntryNotFoundError
    try:
        try:
            snapshot = Path(snapshot_download(repo_id=clean_model_name, revision=RERANKER_REVISION,
                                               local_files_only=True))
        except LocalEntryNotFoundError:
            snapshot = Path(snapshot_download(repo_id=clean_model_name, revision=RERANKER_REVISION))
        weight = snapshot / "model.safetensors"
        if snapshot.name != RERANKER_REVISION or not weight.is_file():
            raise RerankerIntegrityError("Reranker Snapshot 不符合固定版本。")
        checksum = sha256()
        with weight.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                checksum.update(block)
        if checksum.hexdigest() != RERANKER_WEIGHTS_SHA256:
            raise RerankerIntegrityError("Reranker 權重驗證失敗。")
        options = {"batch_size": batch_size, "max_length": max_length, "normalize": True}
        if device in (None, "auto"):
            import torch
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        options["devices"] = [device]
        return FlagReranker(str(snapshot), use_fp16=use_fp16, **options)
    except RerankerIntegrityError:
        raise
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise RerankerModelNotFoundError("固定 Reranker revision 或檔案不存在。", cause=exc) from exc
        raise RerankerDownloadError("Reranker 下載服務暫時無法使用。", cause=exc) from exc
    except httpx.RequestError as exc:
        raise RerankerDownloadError("Reranker 下載連線失敗。", cause=exc) from exc
    except Exception as exc:
        if not isinstance(exc, (OSError, RuntimeError, MemoryError)):
            raise
        detail = _error_detail(exc)
        lowered = detail.casefold()
        if _is_memory_error(exc):
            error_type = RerankerMemoryError
        elif any(
            marker in lowered
            for marker in (
                "repository not found",
                "model not found",
                "not a valid model identifier",
                "404 client error",
            )
        ):
            error_type = RerankerModelNotFoundError
        elif any(
            marker in lowered
            for marker in (
                "connection",
                "connect",
                "network",
                "offline",
                "localentrynotfounderror",
                "timeout",
                "timed out",
                "download",
            )
        ):
            error_type = RerankerDownloadError
        else:
            error_type = RerankerLoadError
        raise error_type(
            f"無法載入 Reranker 模型 {clean_model_name}：{detail}"
        ) from exc


def _normalize_scores(raw_scores: Any) -> list[float]:
    if isinstance(raw_scores, Real):
        values = [raw_scores]
    else:
        converted = raw_scores.tolist() if hasattr(raw_scores, "tolist") else raw_scores
        values = [converted] if isinstance(converted, Real) else list(converted)

    scores: list[float] = []
    for value in values:
        if not isinstance(value, Real):
            raise ValueError("Reranker 分數必須是數值。")
        score = float(value)
        if not isfinite(score):
            raise ValueError("Reranker 分數必須是有限數值。")
        scores.append(score)
    return scores


def rerank_documents(
    question: str,
    documents: Sequence[Document],
    reranker: Any,
    top_k: int,
) -> list[Document]:
    """依相關性分數穩定排序，並保留原始 Document 與 metadata。"""

    clean_question = question.strip()
    if not clean_question:
        raise ValueError("問題不可為空白。")
    if top_k <= 0:
        raise ValueError("top_k 必須大於 0。")
    if not documents:
        return []

    pairs = [[clean_question, document.page_content] for document in documents]
    try:
        raw_scores = reranker.compute_score(pairs, normalize=True)
    except (OSError, RuntimeError, MemoryError) as exc:
        detail = _error_detail(exc)
        if _is_memory_error(exc):
            raise RerankerMemoryError(
                f"Reranker 計算時記憶體不足：{detail}"
            ) from exc
        raise RerankerComputeError(f"Reranker 計算失敗：{detail}") from exc

    try:
        scores = _normalize_scores(raw_scores)
    except (TypeError, ValueError) as exc:
        raise RerankerOutputError(f"Reranker 回傳無效分數：{exc}", cause=exc) from exc
    if len(scores) != len(documents):
        raise RerankerOutputError(
            "Reranker 分數數量與候選文件數量不同："
            f"{len(scores)} != {len(documents)}。"
        )

    ranked = sorted(
        enumerate(documents),
        key=lambda item: scores[item[0]],
        reverse=True,
    )
    return [document for _, document in ranked[:top_k]]
