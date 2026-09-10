"""應用程式設定與環境變數驗證。"""

from __future__ import annotations

import os
import json
from math import isfinite
from .retrieval_errors import RetrievalConfigError
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def validate_release_defaults(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "hybrid_search_enabled"}:
        raise RetrievalConfigError("release_defaults.json 欄位不完整或包含未知欄位。")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise RetrievalConfigError("release_defaults.json schema_version 必須為 1。")
    if type(value["hybrid_search_enabled"]) is not bool:
        raise RetrievalConfigError("release_defaults.json hybrid_search_enabled 必須為布林值。")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "bge-m3"
    chat_model: str = "qwen3:4b"
    chunk_size: int = 500
    chunk_overlap: int = 80
    top_k: int = 8
    hybrid_search_enabled: bool = False
    bm25_top_k: int = 20
    fusion_top_k: int = 30
    rrf_k: int = 60
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    bm25_epsilon: float = 0.25
    reranker_enabled: bool = True
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_use_fp16: bool = False
    reranker_device: str = "auto"
    reranker_batch_size: int = 16
    reranker_max_length: int = 512
    reranker_revision: str = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
    reranker_weights_sha256: str = "d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286"
    retrieval_top_k: int = 20
    ocr_mode: str = "auto"
    ocr_lang: str = "ch"
    ocr_min_text_chars: int = 30
    ocr_dpi: int = 300
    ocr_enable_images: bool = True
    ocr_enable_mkldnn: bool = False
    vlm_enabled: bool = False
    vlm_model: str = "qwen3-vl:4b"
    vlm_mode: str = "auto"
    vlm_max_image_edge: int = 1600
    vlm_timeout_seconds: int = 120
    vlm_num_predict: int = 800
    excel_max_file_size_mb: int = 20
    excel_max_sheets: int = 30
    excel_max_row_index: int = 50_000
    excel_max_column_index: int = 200
    excel_max_cell_chars: int = 3_000
    excel_max_row_chars: int = 4_000
    excel_max_chunk_chars: int = 4_096

    def __post_init__(self) -> None:
        if self.reranker_batch_size <= 0 or self.reranker_max_length <= 0:
            raise RetrievalConfigError("Reranker batch size 與 max length 必須大於 0。")
        if self.reranker_enabled:
            from .reranker import RERANKER_REVISION, RERANKER_WEIGHTS_SHA256
            if self.reranker_revision != RERANKER_REVISION or self.reranker_weights_sha256 != RERANKER_WEIGHTS_SHA256:
                raise RetrievalConfigError("Reranker 身分必須符合固定 revision 與權重 SHA-256。")
        if self.hybrid_search_enabled:
            if self.bm25_top_k <= 0 or self.rrf_k <= 0 or not self.top_k <= self.fusion_top_k <= self.retrieval_top_k + self.bm25_top_k:
                raise RetrievalConfigError("Hybrid 候選數或 RRF K 不合法。")
            if not all(isfinite(v) for v in (self.bm25_k1, self.bm25_b, self.bm25_epsilon)) or self.bm25_k1 <= 0 or not 0 <= self.bm25_b <= 1 or self.bm25_epsilon < 0:
                raise RetrievalConfigError("BM25 參數不合法。")
        for name in (
            "excel_max_file_size_mb", "excel_max_sheets", "excel_max_row_index",
            "excel_max_column_index", "excel_max_cell_chars", "excel_max_row_chars",
            "excel_max_chunk_chars",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name.upper()} 必須大於 0。")
        if self.excel_max_row_chars + 37 > self.excel_max_chunk_chars:
            raise ValueError("EXCEL_MAX_ROW_CHARS + 37 必須小於或等於 EXCEL_MAX_CHUNK_CHARS。")
        if self.chunk_size <= 0:
            raise ValueError("CHUNK_SIZE 必須大於 0。")
        if self.chunk_overlap < 0:
            raise ValueError("CHUNK_OVERLAP 不可小於 0。")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP 必須小於 CHUNK_SIZE。")
        if self.top_k <= 0:
            raise ValueError("TOP_K 必須大於 0。")
        if self.retrieval_top_k <= 0:
            raise ValueError("RETRIEVAL_TOP_K 必須大於 0。")
        if self.retrieval_top_k < self.top_k:
            raise ValueError("RETRIEVAL_TOP_K 必須大於或等於 TOP_K。")
        if not self.reranker_model.strip():
            raise ValueError("RERANKER_MODEL 不可為空白。")
        if self.ocr_mode not in {"auto", "force", "disabled"}:
            raise ValueError("OCR_MODE 必須是 auto、force 或 disabled。")
        if self.ocr_min_text_chars < 0:
            raise ValueError("OCR_MIN_TEXT_CHARS 不可小於 0。")
        if self.ocr_dpi <= 0:
            raise ValueError("OCR_DPI 必須大於 0。")
        if self.vlm_mode not in {"auto", "all", "disabled"}:
            raise ValueError("VLM_MODE 必須是 auto、all 或 disabled。")
        if self.vlm_max_image_edge <= 0:
            raise ValueError("VLM_MAX_IMAGE_EDGE 必須大於 0。")
        if self.vlm_timeout_seconds <= 0:
            raise ValueError("VLM_TIMEOUT_SECONDS 必須大於 0。")
        if self.vlm_num_predict <= 0:
            raise ValueError("VLM_NUM_PREDICT 必須大於 0。")
        if self.vlm_enabled and not self.vlm_model.strip():
            raise ValueError("啟用 VLM 時，VLM_MODEL 不可為空白。")


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} 必須是整數，目前值為 {raw_value!r}。") from exc


def _read_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().casefold()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"{name} 必須是布林值，目前值為 {raw_value!r}。")


def load_settings(
    *,
    env_path: Path | None = None,
    override_env: bool = False,
) -> Settings:
    """從 .env 與環境變數建立並驗證設定。"""

    load_dotenv(
        dotenv_path=env_path or PROJECT_ENV_PATH,
        override=override_env,
    )
    defaults = Settings()
    release = validate_release_defaults(json.loads(
        Path(__file__).with_name("release_defaults.json").read_text(encoding="utf-8")
    ))
    hybrid = _read_bool("HYBRID_SEARCH_ENABLED", release["hybrid_search_enabled"])
    hybrid_values = {}
    if hybrid:
        for key in ("bm25_top_k", "fusion_top_k", "rrf_k"):
            hybrid_values[key] = _read_int(key.upper(), getattr(defaults, key))
        for key in ("bm25_k1", "bm25_b", "bm25_epsilon"):
            try:
                hybrid_values[key] = float(os.getenv(key.upper(), getattr(defaults, key)))
            except ValueError as exc:
                raise RetrievalConfigError("BM25 參數必須是數字。") from exc
    return Settings(
        hybrid_search_enabled=hybrid, **hybrid_values,
        **{
            name: _read_int(name.upper(), getattr(defaults, name))
            for name in (
                "excel_max_file_size_mb", "excel_max_sheets", "excel_max_row_index",
                "excel_max_column_index", "excel_max_cell_chars", "excel_max_row_chars",
                "excel_max_chunk_chars",
            )
        },
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", defaults.ollama_base_url),
        embedding_model=os.getenv("EMBEDDING_MODEL", defaults.embedding_model),
        chat_model=os.getenv("CHAT_MODEL", defaults.chat_model),
        chunk_size=_read_int("CHUNK_SIZE", defaults.chunk_size),
        chunk_overlap=_read_int("CHUNK_OVERLAP", defaults.chunk_overlap),
        top_k=_read_int("TOP_K", defaults.top_k),
        reranker_enabled=_read_bool(
            "RERANKER_ENABLED", defaults.reranker_enabled
        ),
        reranker_model=os.getenv("RERANKER_MODEL", defaults.reranker_model),
        reranker_revision=os.getenv("RERANKER_REVISION", defaults.reranker_revision),
        reranker_weights_sha256=os.getenv("RERANKER_WEIGHTS_SHA256", defaults.reranker_weights_sha256),
        reranker_device=os.getenv("RERANKER_DEVICE", defaults.reranker_device),
        reranker_batch_size=_read_int("RERANKER_BATCH_SIZE", defaults.reranker_batch_size),
        reranker_max_length=_read_int("RERANKER_MAX_LENGTH", defaults.reranker_max_length),
        reranker_use_fp16=_read_bool(
            "RERANKER_USE_FP16", defaults.reranker_use_fp16
        ),
        retrieval_top_k=_read_int(
            "RETRIEVAL_TOP_K", defaults.retrieval_top_k
        ),
        ocr_mode=os.getenv("OCR_MODE", defaults.ocr_mode).strip().casefold(),
        ocr_lang=os.getenv("OCR_LANG", defaults.ocr_lang),
        ocr_min_text_chars=_read_int(
            "OCR_MIN_TEXT_CHARS", defaults.ocr_min_text_chars
        ),
        ocr_dpi=_read_int("OCR_DPI", defaults.ocr_dpi),
        ocr_enable_images=_read_bool(
            "OCR_ENABLE_IMAGES", defaults.ocr_enable_images
        ),
        ocr_enable_mkldnn=_read_bool(
            "OCR_ENABLE_MKLDNN", defaults.ocr_enable_mkldnn
        ),
        vlm_enabled=_read_bool("VLM_ENABLED", defaults.vlm_enabled),
        vlm_model=os.getenv("VLM_MODEL", defaults.vlm_model),
        vlm_mode=os.getenv("VLM_MODE", defaults.vlm_mode).strip().casefold(),
        vlm_max_image_edge=_read_int(
            "VLM_MAX_IMAGE_EDGE", defaults.vlm_max_image_edge
        ),
        vlm_timeout_seconds=_read_int(
            "VLM_TIMEOUT_SECONDS", defaults.vlm_timeout_seconds
        ),
        vlm_num_predict=_read_int(
            "VLM_NUM_PREDICT", defaults.vlm_num_predict
        ),
    )
