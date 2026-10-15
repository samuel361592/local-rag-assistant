"""Background jobs must deliver hybrid state and complete on the UI queue."""
import pytest
import app
from src.rag.config import Settings
from src.rag.rag_service import RagResult


@pytest.mark.parametrize("hybrid", [False, True])
def test_background_answer_receives_knowledge_state(monkeypatch, hybrid):
    vector, bm25, registry = object(), object() if hybrid else None, {"chunk": object()}
    settings = Settings(hybrid_search_enabled=hybrid)
    received = []

    class Service:
        def __init__(self, actual_vector, actual_settings, **kwargs):
            received.append((actual_vector, actual_settings, kwargs))

        def answer_stream(self, question, **kwargs):
            kwargs["token_callback"]("answer")
            return RagResult("answer", [], [])

    monkeypatch.setattr(app, "RagService", Service)
    job = app.start_rag_job(" query ", vector, settings, bm25, registry)
    job.thread.join(timeout=5)
    assert not job.thread.is_alive()
    app.drain_rag_job_updates(job)
    assert job.status == "completed"
    assert job.result.answer == "answer"
    assert received == [(vector, settings, {"bm25_store": bm25, "chunk_registry": registry})]
