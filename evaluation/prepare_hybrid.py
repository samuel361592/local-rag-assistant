"""Create the initial immutable synthetic fixture and evaluation inputs once."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
from openpyxl import Workbook

from src.rag.acceptance import environment_manifest, model_digests
from src.rag.config import Settings
from src.rag.document_loader import process_uploaded_documents
from src.rag.reranker import RERANKER_REVISION, RERANKER_WEIGHTS_SHA256


class Upload(BytesIO):
    def __init__(self, data, name):
        super().__init__(data)
        self.name = name


def prepare(root):
    fixture = root / "evaluation/fixtures/hybrid_identifiers.xlsx"
    dataset_path = root / "evaluation/dataset.hybrid-v1.json"
    config_path = root / "evaluation/config.hybrid-v1.json"
    if any(p.exists() for p in (fixture, dataset_path, config_path)):
        raise FileExistsError("Versioned evaluation inputs already exist; do not overwrite.")
    fixture.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    workbook.remove(workbook.active)
    records = [
        ("FU038", "維修單來源識別欄位", "哪個欄位記錄維修單來源？"),
        ("ABC-123", "溫度感測器設備型號", "要查溫度感測器的維護資訊"),
        ("ZX900", "備援電源產品型號", "要查備援電源的產品資料"),
        ("SOURCE_NOT_FOUND", "來源文件不存在時回傳的錯誤碼", "找不到來源文件時如何判斷原因"),
        ("REPAIR_PENDING", "維修尚未完成的狀態錯誤碼", "如何辨識維修仍在處理中"),
        ("/REP/TobeRepair/Query", "查詢待維修清單的 API", "想查詢待維修清單"),
        ("/CRM/Customer/Lookup", "查詢客戶資料的 API", "需要依客戶資訊查詢資料"),
        ("2026-09-08", "測試設備正式啟用日期", "測試設備何時正式啟用"),
        ("09:30", "每日維修報表產生時間", "每天什麼時間產生維修報表"),
        ("1.8.0", "首次支援維修來源查詢的版本", "哪個版本開始支援維修來源查詢"),
    ]
    for i, (identifier, description, _) in enumerate(records):
        sheet = workbook.create_sheet(f"Record{i+1:02}")
        sheet.append(["識別字", "用途"])
        sheet.append([identifier, description])
    workbook.save(fixture)
    paths = [root / "documents/evaluation/NIST.AI.100-1.pdf",
             root / "documents/evaluation/NIST.AI.600-1.pdf", fixture]
    sources = [{"path": p.relative_to(root).as_posix(), "sha256": sha256(p.read_bytes()).hexdigest()} for p in paths]
    settings = Settings(ocr_mode="disabled", vlm_enabled=False, hybrid_search_enabled=True)
    batch = process_uploaded_documents([Upload(p.read_bytes(), p.name) for p in paths], settings)
    old = json.loads((root / "evaluation/dataset.json").read_text(encoding="utf-8"))
    questions = []
    for i, item in enumerate(old):
        found = [d for d in batch.chunks if d.metadata["source_filename"] == item["expected_source"]
                 and item["expected_text"] in d.page_content]
        if not found:
            raise ValueError(f"Existing gold not found: {item['expected_text']}")
        doc = found[0]
        category = "semantic_paraphrase" if i < 20 else "exact_term"
        question = item["question"] if i < 20 else f"文件中「{item['expected_text']}」的意思與用途是什麼？"
        questions.append({"id": f"{category}_{i+1:03}", "category": category, "question": question,
                          "gold_targets": [{"source_content_sha256": doc.metadata["source_content_sha256"],
                                            "location": {k: doc.metadata[k] for k in ("page", "chunk_ordinal", "content_type", "extraction_method")},
                                            "expected_text": item["expected_text"]}]})
    for i, (identifier, description, intent) in enumerate(records):
        target = {"source_content_sha256": sources[2]["sha256"],
                  "location": {"sheet_name": f"Record{i+1:02}", "row_start": 2, "row_end": 2}, "expected_text": identifier}
        for category, question in [("exact_identifier", f"{identifier} 代表什麼？"),
                                   ("mixed_semantic_exact", f"{intent}，請說明 {identifier} 的用途。")]:
            questions.append({"id": f"{category}_{i+1:03}", "category": category, "question": question, "gold_targets": [target]})
    dataset = {"version": "hybrid-eval-v1", "sources": sources, "questions": questions}
    from src.rag.chunk_identity import build_registry
    from src.rag.hybrid_evaluation import preflight_gold
    preflight_gold(dataset, build_registry(batch.chunks))
    digests = model_digests(settings.ollama_base_url, {"embedding": "bge-m3:latest", "generator": "qwen3:4b"})
    import torch
    config = {
        "evaluation_depth": 20, "answer_top_k": 8, "tokenizer_version": "bm25-tokenizer-v1",
        "retrieval_execution_mode": "sequential_dense_then_bm25", "cache_policy": "acceptance-cache-v1",
        "environment_manifest": "evaluation/environments/hybrid-v1.json", "models": digests,
        "reranker_identity": {"repo_id": "BAAI/bge-reranker-v2-m3", "revision": RERANKER_REVISION, "weights_sha256": RERANKER_WEIGHTS_SHA256},
        "reranker_inference": {"device": "cpu", "use_fp16": False, "dtype": "float32", "batch_size": 16, "max_length": 512, "normalize": True},
        "threads": torch.get_num_threads(), "seed": 20260908, "rank_bm25_version": "0.2.2",
        "settings": {"embedding_model": "bge-m3:latest", "chat_model": "qwen3:4b", "chunk_size": 500, "chunk_overlap": 80,
                     "top_k": 8, "retrieval_top_k": 20, "bm25_top_k": 20, "fusion_top_k": 30, "rrf_k": 60,
                     "bm25_k1": 1.5, "bm25_b": 0.75, "bm25_epsilon": 0.25,
                     "hybrid_search_enabled": True, "reranker_enabled": True, "ocr_mode": "disabled", "vlm_enabled": False}}
    for path, value in [(dataset_path, dataset), (config_path, config),
                        (root / config["environment_manifest"], environment_manifest())]:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(f"Prepared {len(questions)} questions and {len(batch.chunks)} chunks.")
