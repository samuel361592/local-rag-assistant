"""BM25 with versioned, identifier-preserving Chinese tokenization."""
from datetime import date
from functools import lru_cache
from importlib.metadata import version
from math import isfinite
from pathlib import Path
import re
import unicodedata

from .retrieval_errors import BM25SearchError, RetrievalConfigError, UserInputError

TOKENIZER_VERSION = "bm25-tokenizer-v1"
API = re.compile(r"/(?:(?:[A-Za-z0-9._~-]|%[0-9A-Fa-f]{2})+(?:/(?:[A-Za-z0-9._~-]|%[0-9A-Fa-f]{2})+)*/?)?(?:[?](?:[A-Za-z0-9._~!$&()*+,;=:@/?+-]|%[0-9A-Fa-f]{2})*)?", re.ASCII)
TIME_PATTERN = r"(?<![0-9])(?:[01][0-9]|2[0-3]):[0-5][0-9](?::[0-5][0-9])?(?![0-9])"
PATTERNS = [
    (re.compile(r"(?<![0-9])[0-9]{4}-[0-9]{2}-[0-9]{2}(?![0-9])"), 10, "date"),
    (re.compile(TIME_PATTERN), 8, "time"),
    (re.compile(r"v?[0-9]+(?:\.[0-9]+){1,3}(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?"), 128, "version"),
    (re.compile(r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+"), 128, "underscore"),
    (re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+"), 128, "hyphen"),
    (re.compile(r"[A-Za-z0-9]+"), 128, "mixed"),
]
WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+")
BOUNDARY = re.compile(r"[A-Za-z0-9_]")
CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


@lru_cache(maxsize=1)
def _chinese():
    import jieba
    if version("jieba") != "0.42.1":
        raise RetrievalConfigError("jieba 版本不符合 Tokenizer 規格。")
    tokenizer = jieba.Tokenizer()
    tokenizer.load_userdict(str(Path(__file__).with_name("tokenizer_userdict.txt")))
    return tokenizer


def _expand(text):
    parts = [text.casefold()]
    for word in re.findall(r"[A-Za-z]+|[0-9]+", text):
        parts.append(word.casefold())
        parts.extend(w.casefold() for w in CAMEL.split(word))
    return list(dict.fromkeys(parts))


def _api_tokens(target, stats):
    path, sep, query = target.partition("?")
    result = [target.casefold()]
    if path.casefold() != result[0]:
        result.append(path.casefold())
    for segment in path.split("/"):
        if segment:
            result.extend(_expand(segment))
    if sep:
        for pair in re.split(r"[&;]", query):
            name, _, value = pair.partition("=")
            if name:
                result.append(name.casefold())
            if value:
                result.extend(_tokenize(value, allow_api=False, stats=stats))
    return result


def _tokenize(text, *, allow_api=True, stats=None):
    if stats is None:
        stats = {"identifier_overflow_count": 0}
    result = []
    i = 0
    while i < len(text):
        if allow_api and text[i] == "/" and (i == 0 or not re.match(r"[A-Za-z0-9_%]", text[i-1])):
            end = i + 1
            while end < len(text) and 32 < ord(text[end]) < 127 and text[end] not in "#'\"<>":
                end += 1
            target = text[i:end]
            if len(target) <= 2048 and API.fullmatch(target):
                result.extend(_api_tokens(target, stats)); i = end; continue
            if len(target) > 2048:
                stats["identifier_overflow_count"] += 1
            # A rejected target cannot yield a valid API prefix or nested suffix.
            result.extend(_tokenize(target, allow_api=False, stats=stats)); i = end; continue
        matches = []
        for priority, (pattern, limit, kind) in enumerate(PATTERNS):
            match = pattern.match(text, i)
            if not match:
                continue
            value = match.group()
            end = match.end()
            if (i and BOUNDARY.fullmatch(text[i-1])) or (end < len(text) and BOUNDARY.fullmatch(text[end])):
                continue
            if len(value) > limit:
                stats["identifier_overflow_count"] += 1
                continue
            if kind == "date":
                try:
                    date.fromisoformat(value)
                except ValueError:
                    continue
            if kind in {"hyphen", "mixed"} and not re.search("[A-Za-z]", value):
                continue
            if kind == "mixed" and not re.search("[0-9]", value):
                continue
            matches.append((len(value), -priority, value))
        if matches:
            value = max(matches)[2]
            result.extend(_expand(value)); i += len(value); continue
        match = WORD.match(text, i)
        if match:
            value = match.group()
            result.extend(dict.fromkeys([value.casefold(), *(p.casefold() for p in CAMEL.split(value))]))
            i = match.end(); continue
        if "\u3400" <= text[i] <= "\u9fff":
            end = i + 1
            while end < len(text) and "\u3400" <= text[end] <= "\u9fff":
                end += 1
            result.extend(t for t in _chinese().lcut(text[i:end], HMM=False) if t.strip())
            i = end; continue
        i += 1
    return result


def tokenize_for_bm25(text):
    return _tokenize(re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)))


def tokenizer_stats(text):
    stats = {"identifier_overflow_count": 0}
    _tokenize(re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)), stats=stats)
    return stats


class BM25Store:
    @classmethod
    def from_documents(cls, documents, *, k1=1.5, b=0.75, epsilon=0.25):
        if not documents:
            raise RetrievalConfigError("不可建立零 Chunk 知識庫。")
        if not all(isfinite(v) for v in (k1, b, epsilon)) or k1 <= 0 or not 0 <= b <= 1 or epsilon < 0:
            raise RetrievalConfigError("BM25 參數不合法。")
        tokenized = [(doc, tokenize_for_bm25(doc.page_content)) for doc in documents]
        searchable = [(doc, tokens) for doc, tokens in tokenized if tokens]
        store = cls() if searchable else EmptyBM25Store()
        store.source_document_count = len(documents)
        store.searchable_document_count = len(searchable)
        store.documents = list(documents)
        store.searchable = [doc for doc, _ in searchable]
        store.status = "ready" if searchable else "empty_no_tokens"
        store.index = None
        if searchable:
            from rank_bm25 import BM25Okapi
            if version("rank-bm25") != "0.2.2":
                raise RetrievalConfigError("rank-bm25 版本不符合規格。")
            store.index = BM25Okapi([tokens for _, tokens in searchable], k1=k1, b=b, epsilon=epsilon)
        return store

    def search(self, question, top_k):
        from .hybrid_retriever import RankedDocument
        if not question.strip():
            raise UserInputError("請先輸入問題。")
        if top_k <= 0:
            raise RetrievalConfigError("BM25 Top-K 必須大於 0。")
        tokens = tokenize_for_bm25(question)
        if not tokens or self.index is None:
            return []
        try:
            scores = self.index.get_scores(tokens)
        except (ArithmeticError, RuntimeError) as exc:
            raise BM25SearchError("關鍵字檢索計算失敗。", cause=exc) from exc
        if len(scores) != len(self.searchable) or not all(isfinite(float(s)) for s in scores):
            raise BM25SearchError("關鍵字檢索回傳無效分數。")
        ranked = sorted(((doc, float(score)) for doc, score in zip(self.searchable, scores) if score > 0),
                        key=lambda item: (-item[1], item[0].metadata["chunk_id"]))[:top_k]
        return [RankedDocument(doc.metadata["chunk_id"], doc, i, score)
                for i, (doc, score) in enumerate(ranked, 1)]


class EmptyBM25Store(BM25Store):
    pass
