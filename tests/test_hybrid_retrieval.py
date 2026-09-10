from dataclasses import replace
from hashlib import sha256
import pytest
from langchain_core.documents import Document
from src.rag.bm25_store import tokenize_for_bm25, BM25Store, EmptyBM25Store
from src.rag.chunk_identity import assign_chunk_ids, build_registry, validate_candidates
from src.rag.config import Settings, load_settings
from src.rag.hybrid_retriever import ranked_documents, reciprocal_rank_fusion
from src.rag.retrieval_errors import (RetrievalInvariantError, BM25SearchError,
    DenseRetrievalError, KnowledgeStateError, RerankerOutputError)
from src.rag.rag_service import RagService
from src.rag.knowledge_state import transactional_commit
from src.rag.hybrid_evaluation import exact_metrics, quality_gate


def documents(contents):
    docs = [Document(page_content=s, metadata={"source_type": "pdf", "content_type": "text",
           "text_extraction_method": "native", "page_number": i+1, "source_filename": "a.pdf"})
           for i, s in enumerate(contents)]
    return assign_chunk_ids(docs, {"a.pdf": sha256(b"source").hexdigest()})


@pytest.mark.parametrize("text,expected", [
    ("欄位FU038代表什麼？", ["欄位", "fu038", "fu", "038", "代表", "什麼"]),
    ("呼叫/REP/TobeRepair/Query失敗", ["呼叫", "/rep/toberepair/query", "rep", "toberepair", "tobe", "repair", "query", "失敗"]),
    ("於2026-09-08 09:30執行", ["於", "2026-09-08", "2026", "09", "08", "09:30", "09", "30", "執行"]),
    ("型號ABC-123／欄位ＦＵ０３８", ["型號", "abc-123", "abc", "123", "欄位", "fu038", "fu", "038"]),
    ("/api/items?id=id&id=A-1", ["/api/items?id=id&id=a-1", "/api/items", "api", "items", "id", "id", "id", "a-1", "a", "1"]),
    ("/api/api", ["/api/api", "api", "api"]),
    ("！！！", []),
])
def test_token_contract(text, expected):
    assert tokenize_for_bm25(text) == expected


def test_bm25_original_documents_and_empty():
    docs = documents(["FU038 維修編號", "apple banana", "orange lemon", "cloud rain", "！！！"])
    store = BM25Store.from_documents(docs)
    assert store.source_document_count == 5
    assert store.searchable_document_count == 4
    hit = store.search("fu038", 20)
    assert len(hit) == 1 and hit[0].document is next(d for d in docs if "FU038" in d.page_content)
    assert store.search("unseen", 20) == []
    empty = BM25Store.from_documents(documents(["！！！"]))
    assert isinstance(empty, EmptyBM25Store) and empty.search("hello", 20) == []
    store.index.get_scores = lambda _: [float("nan")] * 4
    with pytest.raises(BM25SearchError): store.search("fu038", 20)


def test_rrf_dedup_and_corruption():
    a, b, c = documents(["a", "b", "c"])
    out = reciprocal_rank_fusion([ranked_documents([a, b]), ranked_documents([b, c])], 60, 3)
    assert out[0] is b and len(out) == 3
    assert reciprocal_rank_fusion([ranked_documents([a, a, c]), []], 60, 3) == [a, c]
    corrupt = Document(page_content="changed", metadata=a.metadata)
    with pytest.raises(RetrievalInvariantError):
        ranked_documents([a, corrupt])
    with pytest.raises(RetrievalInvariantError):
        validate_candidates([corrupt], build_registry([a, b, c]))
    faiss_copy = Document(id="faiss-internal-id", page_content=a.page_content, metadata={**a.metadata, "debug": True})
    assert len(reciprocal_rank_fusion([ranked_documents([a]), ranked_documents([faiss_copy])], 60, 3)) == 1


def test_disabled_settings_ignore_invalid_hybrid(monkeypatch, tmp_path):
    monkeypatch.setenv("HYBRID_SEARCH_ENABLED", "false")
    for key in ("BM25_K1", "BM25_TOP_K", "FUSION_TOP_K", "RRF_K"):
        monkeypatch.setenv(key, "invalid")
    assert not load_settings(env_path=tmp_path / "missing.env").hybrid_search_enabled
    assert Settings().top_k == 8
    assert Settings(hybrid_search_enabled=True, bm25_b=0, bm25_epsilon=0)


def test_state_rollback():
    class State(dict):
        failed = False
        def __setitem__(self, key, value):
            if key == "bm25_store" and not self.failed:
                self.failed = True
                raise RuntimeError("simulated write failure")
            super().__setitem__(key, value)
    state = State(vector_store="old", bm25_store="old sparse", messages=["old chat"])
    old = dict(state)
    with pytest.raises(KnowledgeStateError):
        transactional_commit(state, {"vector_store": "new", "bm25_store": "new sparse"})
    assert state == old


@pytest.mark.parametrize("dense_error,sparse_empty", [(False, False), (True, False), (True, True)])
def test_query_failure_matrix(dense_error, sparse_empty):
    docs = documents(["FU038", "apple", "orange", "banana"])
    class Vector:
        def similarity_search(self, question, k):
            if dense_error: raise DenseRetrievalError()
            return docs
    class Chat:
        def invoke(self, messages): return "answer"
    bm25 = BM25Store.from_documents(docs)
    if sparse_empty: bm25.search = lambda *args: []
    service = RagService(Vector(), Settings(hybrid_search_enabled=True, reranker_enabled=False),
                         chat_model=Chat(), bm25_store=bm25, chunk_registry=build_registry(docs))
    if dense_error and sparse_empty:
        with pytest.raises(DenseRetrievalError): service.answer("FU038")
    else:
        result = service.answer("FU038")
        assert result.chunks
        assert result.degraded_components == (["dense"] if dense_error else [])


def test_reranker_invalid_output_degrades():
    docs = documents(["one", "two"])
    class Vector:
        def similarity_search(self, question, k): return docs
    class Ranker:
        def compute_score(self, *args, **kwargs): return [float("nan")]
    service = RagService(Vector(), Settings(), chat_model=object(), reranker=Ranker())
    assert service._retrieve_chunks("question") == docs
    assert service.degraded_components == ["reranker"]


@pytest.mark.parametrize("dense_state", ["nonempty", "empty", "error"])
@pytest.mark.parametrize("sparse_state", ["nonempty", "empty", "error"])
def test_all_nine_query_outcomes(dense_state, sparse_state):
    docs = documents(["FU038", "apple", "orange", "banana"])
    class Vector:
        def similarity_search(self, question, k):
            if dense_state == "error": raise DenseRetrievalError()
            return docs if dense_state == "nonempty" else []
    class Sparse:
        status = "ready"
        def search(self, question, k):
            if sparse_state == "error": raise BM25SearchError()
            return ranked_documents(docs) if sparse_state == "nonempty" else []
    class Chat:
        calls = 0
        def invoke(self, messages):
            self.calls += 1
            return "answer"
    chat = Chat()
    service = RagService(Vector(), Settings(hybrid_search_enabled=True, reranker_enabled=False),
        chat_model=chat, bm25_store=Sparse(), chunk_registry=build_registry(docs))
    events = []
    if "error" in (dense_state, sparse_state) and "nonempty" not in (dense_state, sparse_state):
        with pytest.raises((DenseRetrievalError, BM25SearchError)):
            service.answer("question", events.append)
        assert chat.calls == 0
        assert service.retrieval_counts["final_chunk_count"] is None
        assert not any(e.stage == "rerank_skipped" for e in events)
    else:
        result = service.answer("question", events.append)
        assert chat.calls == int("nonempty" in (dense_state, sparse_state))
        assert bool(result.warnings) == ("error" in (dense_state, sparse_state))
