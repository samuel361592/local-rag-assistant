"""Content-addressed source identities, canonical locations and registry validation."""
from collections import defaultdict
from hashlib import sha256
import json
import re

from .retrieval_errors import RetrievalInvariantError

COMBINATIONS = {("pdf", "text", "native"), ("pdf", "text", "ocr"),
                ("pdf", "visual", "vlm"), ("image", "text", "ocr"),
                ("image", "visual", "vlm"), ("excel", "text", "native")}
IDENTITY_KEYS = ("source_id", "source_content_sha256", "source_type", "source_filename",
                 "content_type", "extraction_method", "content_sha256", "page",
                 "sheet_index", "sheet_name", "row_start", "row_end", "chunk_ordinal",
                 "canonical_location_json", "chunk_id")


def digest(text):
    return sha256(text.encode("utf-8")).hexdigest()


def location_for(metadata):
    source = metadata["source_type"]
    keys = ["source_type", "chunk_ordinal"]
    if source == "excel":
        keys += ["sheet_index", "sheet_name", "row_start", "row_end"]
    else:
        keys += ["content_type", "extraction_method"]
        if source == "pdf":
            keys += ["page"]
    return json.dumps({k: metadata[k] for k in keys}, ensure_ascii=False,
                      sort_keys=True, separators=(",", ":"))


def assign_chunk_ids(chunks, source_hashes):
    counts = defaultdict(int)
    for doc in chunks:
        m = doc.metadata
        source = m["source_type"]
        method = "native" if source == "excel" else m.get("text_extraction_method", "native")
        m["extraction_method"] = method
        if (source, m["content_type"], method) not in COMBINATIONS:
            raise RetrievalInvariantError("文件解析類型不合法。")
        m["source_content_sha256"] = source_hashes[m["source_filename"]]
        m["source_id"] = digest("source-v1\0" + source + "\0" + m["source_content_sha256"])
        m["page"] = m.get("page_number") if source == "pdf" else None
        for key in ("sheet_index", "sheet_name", "row_start", "row_end"):
            if source != "excel":
                m[key] = None
        group = ((m["source_id"], m["sheet_index"], m["sheet_name"]) if source == "excel"
                 else (m["source_id"], m["page"], m["content_type"], method))
        m["chunk_ordinal"] = counts[group]
        counts[group] += 1
        m["canonical_location_json"] = location_for(m)
        m["content_sha256"] = digest(doc.page_content)
        m["chunk_id"] = digest("chunk-v1\0" + m["source_id"] + "\0" +
                               m["canonical_location_json"] + "\0" + m["content_sha256"])
    result = sorted(chunks, key=lambda d: (d.metadata["source_id"],
                    d.metadata["canonical_location_json"].encode("utf-8"), d.metadata["chunk_id"]))
    build_registry(result)
    return result


def validate_document(doc):
    m = doc.metadata
    try:
        for key in ("source_id", "source_content_sha256", "content_sha256", "chunk_id"):
            if not re.fullmatch(r"[0-9a-f]{64}", m[key]):
                raise ValueError("Invalid digest")
        numeric = {"chunk_ordinal": 0}
        if m["source_type"] == "pdf":
            numeric["page"] = 1
        elif m["source_type"] == "excel":
            numeric.update(sheet_index=0, row_start=1, row_end=1)
            if m["row_end"] < m["row_start"] or not isinstance(m["sheet_name"], str):
                raise ValueError("Invalid sheet or row range")
        for key, minimum in numeric.items():
            if type(m[key]) is not int or m[key] < minimum:
                raise ValueError("Invalid location")
        valid = (
            (m["source_type"], m["content_type"], m["extraction_method"]) in COMBINATIONS
            and m["canonical_location_json"] == location_for(m)
            and m["content_sha256"] == digest(doc.page_content)
            and m["source_id"] == digest("source-v1\0" + m["source_type"] + "\0" + m["source_content_sha256"])
            and m["chunk_id"] == digest("chunk-v1\0" + m["source_id"] + "\0" +
                                      m["canonical_location_json"] + "\0" + m["content_sha256"])
        )
        if not valid:
            raise ValueError("Identity mismatch")
    except (KeyError, ValueError, TypeError) as exc:
        raise RetrievalInvariantError("知識庫文件身分不一致，請重新建庫。", cause=exc) from exc


def build_registry(chunks):
    registry = {}
    for doc in chunks:
        validate_document(doc)
        key = doc.metadata["chunk_id"]
        if key in registry:
            raise RetrievalInvariantError("知識庫包含重複 Chunk ID。")
        registry[key] = doc
    return registry


def validate_candidates(documents, registry):
    for doc in documents:
        validate_document(doc)
        canonical = registry.get(doc.metadata["chunk_id"])
        if canonical is None or canonical.page_content != doc.page_content or any(
                canonical.metadata.get(k) != doc.metadata.get(k) for k in IDENTITY_KEYS):
            raise RetrievalInvariantError("檢索文件與知識庫不一致。")
