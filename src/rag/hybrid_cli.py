"""CLI entry for versioned hybrid tuning and acceptance runs."""
import argparse
from dataclasses import fields
from io import BytesIO
from pathlib import Path
import json
import os
import sys
import traceback
import platform
import re
from importlib import metadata
import httpx

from .acceptance import (config_id, run_id, model_digests, fingerprint, worktree_check,
                         verify_environment, write_result, git, hash_file, safe_path)
from .bm25_store import BM25Store
from .chunk_identity import build_registry
from .config import Settings
from .document_loader import process_uploaded_documents
from .hybrid_evaluation import run_benchmark
from .reranker import compute_scores, create_reranker, RERANKER_REVISION, RERANKER_WEIGHTS_SHA256
from .retrieval_errors import RetrievalConfigError
from .vector_store import create_vector_store
from .hybrid_cache import cached_vector_store


class NamedUpload(BytesIO):
    def __init__(self, path):
        super().__init__(path.read_bytes())
        self.name = path.name


class ConfiguredReranker:
    def __init__(self, ranker, parameters):
        self.ranker, self.parameters = ranker, parameters

    def compute_score(self, pairs, normalize):
        return compute_scores(self.ranker, pairs, normalize=self.parameters["normalize"],
            batch_size=self.parameters["batch_size"], max_length=self.parameters["max_length"])


def _exact_keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise RetrievalConfigError(f"{label} 欄位不完整或包含未知欄位。")


def validate_pipeline_config(config):
    _exact_keys(config, {"evaluation_depth", "answer_top_k", "tokenizer_version",
        "retrieval_execution_mode", "cache_policy", "environment_manifest", "models",
        "reranker_identity", "reranker_inference", "threads", "seed",
        "rank_bm25_version", "settings"}, "Pipeline Config")
    if type(config["evaluation_depth"]) is not int or config["evaluation_depth"] != 20:
        raise RetrievalConfigError("evaluation_depth 必須為整數 20。")
    if type(config["answer_top_k"]) is not int or config["answer_top_k"] != 8:
        raise RetrievalConfigError("answer_top_k 必須為整數 8。")
    if config["tokenizer_version"] != "bm25-tokenizer-v1":
        raise RetrievalConfigError("Tokenizer 規則版本不符。")
    if config["retrieval_execution_mode"] != "sequential_dense_then_bm25":
        raise RetrievalConfigError("檢索執行順序不符。")
    if config["cache_policy"] != "acceptance-cache-v1":
        raise RetrievalConfigError("Evaluation cache policy 不符。")
    if not isinstance(config["environment_manifest"], str):
        raise RetrievalConfigError("environment_manifest 必須是相對路徑字串。")
    if type(config["threads"]) is not int or config["threads"] <= 0 or type(config["seed"]) is not int:
        raise RetrievalConfigError("threads 與 seed 型別不合法。")
    if config["rank_bm25_version"] != "0.2.2":
        raise RetrievalConfigError("rank-bm25 版本必須為 0.2.2。")

    _exact_keys(config["models"], {"embedding", "generator"}, "models")
    for role, identity in config["models"].items():
        _exact_keys(identity, {"name", "digest"}, f"models.{role}")
        if not isinstance(identity["name"], str) or ":" not in identity["name"]:
            raise RetrievalConfigError(f"models.{role}.name 必須包含明確 tag。")
        if not isinstance(identity["digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", identity["digest"]):
            raise RetrievalConfigError(f"models.{role}.digest 格式錯誤。")

    _exact_keys(config["reranker_identity"], {"repo_id", "revision", "weights_sha256"}, "reranker_identity")
    if config["reranker_identity"] != {"repo_id": "BAAI/bge-reranker-v2-m3",
            "revision": RERANKER_REVISION, "weights_sha256": RERANKER_WEIGHTS_SHA256}:
        raise RetrievalConfigError("Reranker Config 必須使用固定 revision 與權重雜湊。")
    params = config["reranker_inference"]
    _exact_keys(params, {"device", "use_fp16", "dtype", "batch_size", "max_length", "normalize"},
                "reranker_inference")
    if (not isinstance(params["device"], str) or params["device"] == "auto"
            or type(params["use_fp16"]) is not bool or params["normalize"] is not True
            or type(params["batch_size"]) is not int or type(params["max_length"]) is not int
            or params["batch_size"] <= 0 or params["max_length"] <= 0
            or params["dtype"] != ("float16" if params["use_fp16"] else "float32")):
        raise RetrievalConfigError("Reranker inference parameters 不合法。")

    settings = config["settings"]
    allowed = {field.name for field in fields(Settings)} - {"ollama_base_url"}
    required = {"embedding_model", "chat_model", "chunk_size", "chunk_overlap", "top_k",
        "retrieval_top_k", "bm25_top_k", "fusion_top_k", "rrf_k", "bm25_k1", "bm25_b",
        "bm25_epsilon", "hybrid_search_enabled", "reranker_enabled", "ocr_mode", "vlm_enabled"}
    if not isinstance(settings, dict) or not required <= set(settings) or set(settings) - allowed:
        raise RetrievalConfigError("settings 欄位缺失或包含非 Settings 欄位。")
    effective = Settings(**settings)
    if (not effective.hybrid_search_enabled or not effective.reranker_enabled
            or effective.embedding_model != config["models"]["embedding"]["name"]
            or effective.chat_model != config["models"]["generator"]["name"]
            or effective.top_k != config["answer_top_k"]
            or min(effective.retrieval_top_k, effective.bm25_top_k, effective.fusion_top_k)
                < config["evaluation_depth"]):
        raise RetrievalConfigError("settings 與模型或 Hybrid 評測參數不一致。")
    mapping = {"reranker_batch_size": "batch_size", "reranker_max_length": "max_length",
               "reranker_use_fp16": "use_fp16"}
    for setting_name, inference_name in mapping.items():
        if setting_name in settings and settings[setting_name] != params[inference_name]:
            raise RetrievalConfigError(f"settings.{setting_name} 與 reranker_inference 不一致。")
    if not re.fullmatch(r"cpu|cuda:[0-9]+", params["device"]):
        raise RetrievalConfigError("reranker_inference.device 必須解析為單一 CPU 或 CUDA device。")
    if "reranker_device" in settings:
        setting_device = settings["reranker_device"]
        if setting_device == "auto":
            import torch
            setting_device = "cuda:0" if torch.cuda.is_available() else "cpu"
        if setting_device != params["device"]:
            raise RetrievalConfigError("settings.reranker_device 與實際推論裝置不一致。")
    identity_mapping = {"reranker_model": "repo_id", "reranker_revision": "revision",
                        "reranker_weights_sha256": "weights_sha256"}
    for setting_name, identity_name in identity_mapping.items():
        if setting_name in settings and settings[setting_name] != config["reranker_identity"][identity_name]:
            raise RetrievalConfigError(f"settings.{setting_name} 與 reranker_identity 不一致。")
    return effective


def validate_dataset(dataset):
    _exact_keys(dataset, {"version", "sources", "questions"}, "Dataset")
    if dataset["version"] != "hybrid-eval-v1" or not isinstance(dataset["sources"], list):
        raise RetrievalConfigError("Dataset version 或 sources 不合法。")
    seen_paths, seen_hashes = set(), set()
    for source in dataset["sources"]:
        _exact_keys(source, {"path", "sha256"}, "Dataset source")
        if (not isinstance(source["path"], str) or source["path"] in seen_paths
                or not isinstance(source["sha256"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", source["sha256"])):
            raise RetrievalConfigError("Dataset source path 或 SHA-256 不合法。")
        seen_paths.add(source["path"])
        seen_hashes.add(source["sha256"])
    if len(dataset["sources"]) != 3 or len(seen_hashes) != 3 or not isinstance(dataset["questions"], list):
        raise RetrievalConfigError("hybrid-eval-v1 必須引用三份不同語料與問題清單。")
    for question in dataset["questions"]:
        _exact_keys(question, {"id", "category", "question", "gold_targets"}, "Dataset question")
        if (not all(isinstance(question[key], str) for key in ("id", "category", "question"))
                or not isinstance(question["gold_targets"], list)):
            raise RetrievalConfigError("Dataset question 欄位型別錯誤。")
        for target in question["gold_targets"]:
            _exact_keys(target, {"source_content_sha256", "location", "expected_text"}, "Gold target")
            if (target["source_content_sha256"] not in seen_hashes
                    or not isinstance(target["location"], dict) or not target["location"]
                    or not isinstance(target["expected_text"], str)):
                raise RetrievalConfigError("Gold target 內容不合法。")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--hybrid", action="store_true")
    parser.add_argument("--dataset", default="evaluation/dataset.hybrid-v1.json")
    parser.add_argument("--config", default="evaluation/config.hybrid-v1.json")
    parser.add_argument("--run-purpose", choices=("tuning", "acceptance"), default="tuning")
    parser.add_argument("--cache-root", required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    cache = Path(args.cache_root).resolve()
    if cache.is_relative_to(root):
        raise RetrievalConfigError("Benchmark cache root 必須在 Repository 外。")
    cache.mkdir(parents=True, exist_ok=True)
    config_path = safe_path(root, args.config)
    dataset_path = safe_path(root, args.dataset)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    validate_pipeline_config(config)
    validate_dataset(dataset)
    cid = config_id(config)
    commit = git(root, "rev-parse", "HEAD").decode().strip()
    rid = run_id(commit, cid)
    output = root / "evaluation/results" / dataset["version"] / cid / (rid + ".json")
    result = {"run_id": rid, "config_id": cid, "dataset_version": dataset["version"],
              "dataset_sha256": hash_file(root / args.dataset), "config_sha256": hash_file(root / args.config),
              "run_purpose": args.run_purpose, "evaluated_commit": commit, "config": config,
              "cache_root": str(cache), "gate": {"status": "ERROR"}}
    from huggingface_hub.constants import HF_HUB_CACHE
    result["model_cache_root"] = HF_HUB_CACHE
    try:
        if config["evaluation_depth"] != 20 or config["answer_top_k"] != 8:
            raise RetrievalConfigError("Evaluation depth 或 answer_top_k 不符合規格。")
        if config["retrieval_execution_mode"] != "sequential_dense_then_bm25":
            raise RetrievalConfigError("不支援的評測執行模式。")
        if config["reranker_identity"] != {"repo_id": "BAAI/bge-reranker-v2-m3",
                "revision": RERANKER_REVISION, "weights_sha256": RERANKER_WEIGHTS_SHA256}:
            raise RetrievalConfigError("Reranker Config 身分與實際固定模型不符。")
        params = config["reranker_inference"]
        if params["normalize"] is not True or params["batch_size"] <= 0 or params["max_length"] <= 0:
            raise RetrievalConfigError("Reranker 推論參數不合法。")
        settings = Settings(**config["settings"], ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        digests = model_digests(settings.ollama_base_url, {role: value["name"] for role, value in config["models"].items()})
        if digests != config["models"]:
            raise RetrievalConfigError("Ollama 模型 digest 與 Config 不符。")
        for source in dataset["sources"]:
            if hash_file(root / source["path"]) != source["sha256"]:
                raise RetrievalConfigError("評測語料雜湊不符。")
        acceptance = args.run_purpose == "acceptance"
        if acceptance:
            verify_environment(root, config)
            fp, obj = fingerprint(root, args.dataset, args.config, config, dataset, digests)
            worktree_check(root, commit, obj, dataset)
            result.update(pipeline_fingerprint=fp, fingerprint_manifest=obj)
        else:
            result["worktree_status"] = git(root, "status", "--porcelain").decode()
        import torch
        torch.set_num_threads(config["threads"])
        result["runtime"] = {"python": platform.python_version(), "os": platform.platform(),
            "cpu": platform.processor(), "cpu_count": os.cpu_count(), "threads": torch.get_num_threads(),
            "torch": torch.__version__, "cuda": torch.version.cuda, "device": params["device"],
            "ollama": httpx.get(settings.ollama_base_url.rstrip("/") + "/api/version", timeout=30).json(),
            "model_digests": digests,
            "packages": {name: metadata.version(name) for name in
                         ("rank-bm25", "jieba", "FlagEmbedding", "faiss-cpu", "langchain-core")}}
        try:
            import psutil
            result["runtime"]["ram_bytes"] = psutil.virtual_memory().total
        except ImportError:
            raise RetrievalConfigError("缺少 RAM 資訊收集相依套件 psutil。")
        result["reranker_inference"] = params
        print("Loading fixed corpus...", flush=True)
        batch = process_uploaded_documents([NamedUpload(root / source["path"]) for source in dataset["sources"]], settings)
        registry = build_registry(batch.chunks)
        print(f"Building indexes for {len(registry)} chunks...", flush=True)
        vector = cached_vector_store(batch.chunks, settings, config, cache)
        bm25 = BM25Store.from_documents(batch.chunks, k1=settings.bm25_k1, b=settings.bm25_b, epsilon=settings.bm25_epsilon)
        result["source_sha256"] = {source["path"]: source["sha256"] for source in dataset["sources"]}
        result["bm25"] = {"package": bm25.package, "version": bm25.package_version,
            "k1": bm25.k1, "b": bm25.b, "epsilon": bm25.epsilon,
            "source_document_count": bm25.source_document_count,
            "searchable_document_count": bm25.searchable_document_count,
            "excluded_empty_token_count": bm25.source_document_count - bm25.searchable_document_count,
            "identifier_overflow_count": bm25.identifier_overflow_count, "status": bm25.status}
        params = config["reranker_inference"]
        ranker = create_reranker(settings.reranker_model, params["use_fp16"], device=params["device"],
                                batch_size=params["batch_size"], max_length=params["max_length"])
        if ranker.target_devices != [params["device"]]:
            raise RetrievalConfigError("Reranker 實際 device 與 Config 不符。")
        actual_dtype = str(next(ranker.model.parameters()).dtype).removeprefix("torch.")
        if actual_dtype != params["dtype"]:
            raise RetrievalConfigError("Reranker 實際 dtype 與 Config 不符。")
        configured = ConfiguredReranker(ranker, params)
        result.update(run_benchmark(dataset, registry, vector, bm25, configured, settings, progress=lambda s: print(s, flush=True)))
        if acceptance:
            verify_environment(root, config)
            after = model_digests(settings.ollama_base_url, {role: value["name"] for role, value in config["models"].items()})
            new_fp, new_obj = fingerprint(root, args.dataset, args.config, config, dataset, after)
            worktree_check(root, commit, new_obj, dataset)
            if new_fp != fp:
                raise RetrievalConfigError("INVALID_WORKTREE_CHANGED")
        write_result(output, result)
        print(f"{result['gate']['status']}: {output}", flush=True)
        return 0 if result["gate"]["status"] in {"PASSED", "CEILING_NON_INFERIOR"} else 1
    except Exception as exc:
        result.pop("metrics", None)
        result.pop("deltas", None)
        result["gate"] = {"status": "ERROR"}
        result["error"] = {"error_code": getattr(exc, "error_code", "INTERNAL_RETRIEVAL_ERROR"), "message": str(exc)}
        write_result(output, result)
        traceback.print_exc()
        return 1
