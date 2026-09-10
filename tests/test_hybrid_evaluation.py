from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import json
import subprocess
import pytest

from src.rag.acceptance import (config_id, run_id, repository_module_name, safe_path,
                                hash_file, validate_release_manifest, verify_promotion, write_result)
from src.rag.hybrid_evaluation import exact_metrics, quality_gate, fraction_json, percentile, gold_matches
from src.rag.retrieval_errors import RetrievalConfigError
from src.rag.hybrid_cli import validate_dataset, validate_pipeline_config
from langchain_core.documents import Document


def metrics(rank=1):
    categories = ("all", "semantic_paraphrase", "exact_identifier", "mixed_semantic_exact")
    base = {c: exact_metrics([rank]*10) for c in categories}
    return {"CURRENT_BASELINE": deepcopy(base), "TARGET": deepcopy(base)}


def test_ceiling_is_optional_not_default_promotion():
    assert quality_gate(metrics())["status"] == "CEILING_NON_INFERIOR"
    assert quality_gate(metrics(2))["status"] == "FAILED"


def test_quality_requires_predeclared_improvement_and_no_regression():
    m = metrics(2)
    m["TARGET"]["mixed_semantic_exact"]["hit_rate@5"] = Fraction(1)
    m["CURRENT_BASELINE"]["mixed_semantic_exact"]["hit_rate@5"] = Fraction(9, 10)
    assert quality_gate(m)["status"] == "PASSED"
    m["TARGET"]["all"]["mrr@20"] = Fraction(49, 100)
    assert quality_gate(m)["status"] == "FAILED"


def test_exact_rational_aggregation_and_nearest_rank():
    assert exact_metrics([1, 3, None])["mrr@20"] == Fraction(4, 9)
    assert fraction_json(Fraction(1, 3)) == {"numerator": 1, "denominator": 3, "decimal": "0.33333333"}
    assert percentile(list(range(1, 251)), .95) == 238


def test_config_jcs_and_non_overwriting_result(tmp_path):
    assert config_id({"b": 1.0, "a": 2}) == config_id({"a": 2, "b": 1})
    assert config_id({"a": 2}) != config_id({"a": 3})
    result = tmp_path / "result.json"
    write_result(result, {"status": "ERROR"})
    with pytest.raises(FileExistsError): write_result(result, {})
    with pytest.raises(RetrievalConfigError): safe_path(tmp_path, "../outside")


def test_release_manifest_schema_and_cross_field_identity_are_strict():
    commit = "a" * 40
    cid = "b" * 64
    manifest = {"dataset_version": "hybrid-eval-v1", "config_id": cid,
        "run_id": f"20260910T010203123456Z_{commit[:12]}_{cid[:12]}",
        "evaluated_commit": commit, "pipeline_fingerprint": "c" * 64,
        "decision_status": "PASSED", "verified_at": "2026-09-10T01:02:03.123456Z"}
    assert validate_release_manifest(manifest) is manifest
    for key, value in (("decision_status", "FAILED"), ("run_id", "wrong"),
                       ("verified_at", "not-a-timeZ")):
        invalid = {**manifest, key: value}
        with pytest.raises(RetrievalConfigError):
            validate_release_manifest(invalid)
    with pytest.raises(RetrievalConfigError):
        validate_release_manifest({**manifest, "extra": True})


def test_promotion_verifies_git_ancestry_allowed_diff_and_committed_bytes(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args]).decode().strip()

    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True)
    (tmp_path / "src/rag").mkdir(parents=True)
    (tmp_path / "src/rag/release_defaults.json").write_text(
        '{"schema_version":1,"hybrid_search_enabled":false}\n', encoding="utf-8")
    (tmp_path / ".env.example").write_text("HYBRID_SEARCH_ENABLED=false\n", encoding="utf-8")
    (tmp_path / ".gitattributes").write_text("* -text\n", encoding="utf-8")
    (tmp_path / "pipeline.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "evaluated"], check=True, capture_output=True)
    evaluated = git("rev-parse", "HEAD")

    config = {"fixed": True}
    cid = config_id(config)
    rid = f"20260910T010203123456Z_{evaluated[:12]}_{cid[:12]}"
    fingerprint_manifest = {"schema": "pipeline-fingerprint-v2",
        "files": {"pipeline.py": hash_file(tmp_path / "pipeline.py")},
        "models": {}, "runtime": {}}
    fingerprint_id = config_id(fingerprint_manifest)
    result = {"run_purpose": "acceptance", "gate": {"status": "PASSED"},
        "evaluated_commit": evaluated, "pipeline_fingerprint": fingerprint_id,
        "dataset_version": "hybrid-eval-v1", "config_id": cid, "run_id": rid,
        "config": config, "fingerprint_manifest": fingerprint_manifest}
    result_relative = f"evaluation/results/hybrid-eval-v1/{cid}/{rid}.json"
    result_path = tmp_path / result_relative
    result_path.parent.mkdir(parents=True)
    result_path.write_text(json.dumps(result) + "\n", encoding="utf-8")
    manifest = {"dataset_version": "hybrid-eval-v1", "config_id": cid, "run_id": rid,
        "evaluated_commit": evaluated, "pipeline_fingerprint": fingerprint_id,
        "decision_status": "PASSED", "verified_at": "2026-09-10T01:02:03.123456Z"}
    manifest_path = tmp_path / "evaluation/releases/hybrid-default.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    (tmp_path / "src/rag/release_defaults.json").write_text(
        '{"schema_version":1,"hybrid_search_enabled":true}\n', encoding="utf-8")
    (tmp_path / ".env.example").write_text("HYBRID_SEARCH_ENABLED=true\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "promote"], check=True, capture_output=True)
    assert verify_promotion(tmp_path) == manifest
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(RetrievalConfigError):
        verify_promotion(tmp_path)


def test_repository_module_name_does_not_resolve_third_party_relative_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert repository_module_name(tmp_path, "_ops.py") is None
    (tmp_path / "_ops.py").write_text("", encoding="utf-8")
    assert repository_module_name(tmp_path, "_ops.py") == "_ops.py"
    assert repository_module_name(tmp_path, tmp_path / "_ops.py") == "_ops.py"


def test_excel_gold_range_contains_answer_rows():
    doc = Document(page_content="FU038", metadata={"source_content_sha256": "hash", "source_type": "excel",
        "sheet_name": "Fields", "row_start": 2, "row_end": 10})
    target = {"source_content_sha256": "hash", "location": {"sheet_name": "Fields", "row_start": 4, "row_end": 6},
              "expected_text": "FU038"}
    assert gold_matches(doc, target)
    target["location"]["row_end"] = 11
    assert not gold_matches(doc, target)
    target["location"]["row_end"] = 6
    target["expected_text"] = "fu038"
    assert not gold_matches(doc, target)


def test_versioned_dataset_has_fixed_categories_and_source_hashes():
    from collections import Counter
    from src.rag.acceptance import hash_file
    root = Path(__file__).resolve().parents[1]
    dataset = json.loads((root / "evaluation/dataset.hybrid-v1.json").read_text(encoding="utf-8"))
    assert Counter(q["category"] for q in dataset["questions"]) == {
        "semantic_paraphrase": 20, "exact_term": 10, "exact_identifier": 10, "mixed_semantic_exact": 10}
    for source in dataset["sources"]:
        path = root / source["path"]
        if path.is_file():
            assert hash_file(path) == source["sha256"]


def test_versioned_config_and_dataset_pass_strict_schema_validation():
    root = Path(__file__).resolve().parents[1]
    config = json.loads((root / "evaluation/config.hybrid-v6.json").read_text(encoding="utf-8"))
    dataset = json.loads((root / "evaluation/dataset.hybrid-v1.json").read_text(encoding="utf-8"))
    validate_pipeline_config(config)
    validate_dataset(dataset)
    invalid = deepcopy(config)
    invalid["unexpected"] = True
    with pytest.raises(RetrievalConfigError):
        validate_pipeline_config(invalid)
    invalid = deepcopy(config)
    invalid["reranker_inference"]["batch_size"] = 0
    with pytest.raises(RetrievalConfigError):
        validate_pipeline_config(invalid)


def test_four_groups_share_computation_but_never_cache_between_trials():
    from tests.test_hybrid_retrieval import documents
    from src.rag.chunk_identity import build_registry
    from src.rag.hybrid_evaluation import run_benchmark
    from src.rag.config import Settings
    docs = documents([f"content {i}" for i in range(25)])
    gold = docs[0]
    counts = {"dense": 0, "bm25": 0, "reranker": 0}
    class Vector:
        def similarity_search(self, query, k):
            counts["dense"] += 1
            return docs[:k]
    class Sparse:
        def search(self, query, k):
            counts["bm25"] += 1
            return []
    class Reranker:
        def compute_score(self, pairs, normalize):
            counts["reranker"] += 1
            return list(range(len(pairs), 0, -1))
    questions = []
    for category, n in [("semantic_paraphrase", 20), ("exact_term", 10),
                        ("exact_identifier", 10), ("mixed_semantic_exact", 10)]:
        for i in range(n):
            questions.append({"id": f"{category}{i}", "category": category, "question": "content",
                "gold_targets": [{"source_content_sha256": gold.metadata["source_content_sha256"],
                                  "location": {"page": gold.metadata["page"]}, "expected_text": gold.page_content}]})
    result = run_benchmark({"questions": questions}, build_registry(docs), Vector(), Sparse(), Reranker(),
                           Settings(hybrid_search_enabled=True))
    assert counts == {"dense": 300, "bm25": 300, "reranker": 600}
    assert len(result["rows"]) == 1000
    assert result["gate"]["status"] == "CEILING_NON_INFERIOR"
    assert len(result["trial_metrics"]) == 5
