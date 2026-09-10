"""Rank-only fusion; scores from different retrieval systems never mix."""
from dataclasses import dataclass
from fractions import Fraction
from math import inf
from langchain_core.documents import Document
from .retrieval_errors import RetrievalInvariantError, RetrievalConfigError
from .chunk_identity import IDENTITY_KEYS


def _same_chunk(left, right):
    return left.page_content == right.page_content and all(
        left.metadata.get(key) == right.metadata.get(key) for key in IDENTITY_KEYS)


@dataclass(frozen=True, slots=True)
class RankedDocument:
    chunk_id: str
    document: Document
    rank: int
    score: float | None = None


def ranked_documents(documents):
    seen = {}
    result = []
    for doc in documents:
        key = doc.metadata["chunk_id"]
        if key in seen:
            if not _same_chunk(seen[key], doc):
                raise RetrievalInvariantError("同一 Chunk ID 對應不同文件。")
            continue
        seen[key] = doc
        result.append(RankedDocument(key, doc, len(result) + 1))
    return result


def reciprocal_rank_fusion(rankings, rrf_k, top_k):
    if rrf_k <= 0 or top_k <= 0:
        raise RetrievalConfigError("RRF K 與 Top-K 必須大於 0。")
    docs, scores, ranks = {}, {}, {}
    for index, ranking in enumerate(rankings):
        clean = ranked_documents([r.document for r in ranking])
        for item in clean:
            key = item.chunk_id
            if key in docs and not _same_chunk(docs[key], item.document):
                raise RetrievalInvariantError("跨檢索器 Chunk 不一致。")
            docs[key] = item.document
            scores[key] = scores.get(key, Fraction()) + Fraction(1, rrf_k + item.rank)
            ranks.setdefault(key, {})[index] = item.rank
    order = sorted(docs, key=lambda key: (-scores[key], -len(ranks[key]),
                   ranks[key].get(0, inf), ranks[key].get(1, inf), key))
    return [docs[key] for key in order[:top_k]]
