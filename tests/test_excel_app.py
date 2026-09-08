from io import BytesIO
from pathlib import Path

import pytest
import streamlit as st
from openpyxl import Workbook
from streamlit.testing.v1 import AppTest

from src.rag import config, vector_store
from src.rag.config import Settings


def excel_file(name="sales.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append(["產品", "營收"])
    ws.append(["A", 20])
    stream = BytesIO()
    wb.save(stream)
    stream.name = name
    return stream


@pytest.fixture
def app_environment(monkeypatch):
    files = [excel_file()]
    calls = []
    flags = {"fail": False}
    def build(chunks, settings):
        calls.append(chunks)
        if flags["fail"]:
            raise RuntimeError("private model internals")
        return {"generation": len(calls)}
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: files)
    monkeypatch.setattr(config, "load_settings", lambda: Settings(vlm_enabled=False, reranker_enabled=False))
    monkeypatch.setattr(vector_store, "create_vector_store", build)
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "app.py", default_timeout=30).run()
    assert not app.exception
    return app, files, calls, flags


def build_button(app):
    return next(button for button in app.button if button.label == "建立知識庫")


def test_app_excel_build_stats_preview_and_success_reset(app_environment):
    app, files, calls, flags = app_environment
    build_button(app).click().run()
    assert not app.exception
    assert len(calls) == 1 and calls[0][0].metadata["source_type"] == "excel"
    assert app.session_state["knowledge_stats"]["pages"] == 0
    assert app.session_state["active_knowledge_files"] == ["sales.xlsx"]
    metrics = {m.label: m.value for m in app.metric}
    assert metrics["Excel 工作簿數"] == "1"
    assert metrics["Excel 有效資料列"] == "1"
    assert app.selectbox(key="chunk_preview_sheet").disabled
    app.selectbox(key="chunk_preview_filename").select("sales.xlsx").run()
    assert not app.selectbox(key="chunk_preview_sheet").disabled
    app.selectbox(key="chunk_preview_sheet").select("Sales").run()
    assert any("工作表「Sales」，第 2 列" in exp.label for exp in app.expander)
    app.session_state["chat_history"] = ["old"]
    files[:] = [excel_file("new.xlsx")]
    build_button(app).click().run()
    assert not app.exception
    assert app.session_state["active_knowledge_files"] == ["new.xlsx"]
    assert "chat_history" not in app.session_state
    assert app.selectbox(key="chunk_preview_filename").value == "全部"
    assert app.selectbox(key="chunk_preview_sheet").disabled


@pytest.mark.parametrize("model_failure", [False, True])
def test_failed_batch_keeps_old_state_even_when_filename_same(app_environment, model_failure):
    app, files, calls, flags = app_environment
    build_button(app).click().run()
    old_chunks = app.session_state["knowledge_chunks"]
    old_store = app.session_state["vector_store"]
    old_stats = app.session_state["knowledge_stats"]
    app.selectbox(key="chunk_preview_filename").select("sales.xlsx").run()
    app.session_state["chat_history"] = ["old"]
    if model_failure:
        flags["fail"] = True
    else:
        bad = BytesIO(b"broken")
        bad.name = "sales.xlsx"
        files[:] = [bad]
    build_button(app).click().run()
    assert not app.exception
    assert app.session_state["vector_store"] == old_store
    assert app.session_state["knowledge_chunks"] == old_chunks
    assert app.session_state["knowledge_stats"] == old_stats
    assert app.session_state["chat_history"] == ["old"]
    assert app.selectbox(key="chunk_preview_filename").value == "sales.xlsx"
    assert any("目前仍使用上一版知識庫" in info.value for info in app.info)
    assert all("private model internals" not in error.value for error in app.error)


def test_initial_failure_does_not_create_index(app_environment):
    app, files, calls, flags = app_environment
    flags["fail"] = True
    build_button(app).click().run()
    assert not app.exception
    assert "vector_store" not in app.session_state
    assert not any("上一版知識庫" in info.value for info in app.info)
