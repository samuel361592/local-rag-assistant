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
from importlib import metadata
import httpx

from .acceptance import (config_id, run_id, model_digests, fingerprint, worktree_check,
                         verify_environment, write_result, git, hash_file)
from .bm25_store import BM25Store
from .chunk_identity import build_registry
from .config import Settings
from .document_loader import process_uploaded_documents
from .hybrid_evaluation import run_benchmark
from .reranker import create_reranker, RERANKER_REVISION, RERANKER_WEIGHTS_SHA256
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
        return self.ranker.compute_score(pairs, normalize=self.parameters["normalize"],
            batch_size=self.parameters["batch_size"], max_length=self.parameters["max_length"])


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
    config = json.loads((root / args.config).read_text(encoding="utf-8"))
    dataset = json.loads((root / args.dataset).read_text(encoding="utf-8"))
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
            "model_digests": digests}
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
