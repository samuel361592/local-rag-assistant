"""Describe runtime verification without changing an explicit user setting."""
from pathlib import Path
import json
import subprocess
import httpx


def runtime_verification_status(settings):
    if not settings.hybrid_search_enabled:
        return "disabled"
    root = Path(__file__).resolve().parents[2]
    manifest_path = root / "evaluation/releases/hybrid-default.json"
    if not manifest_path.is_file():
        return "custom_unverified"
    from .acceptance import verify_promotion, environment_manifest, model_digests
    try:
        manifest = verify_promotion(root)
        result_path = root / "evaluation/results" / manifest["dataset_version"] / manifest["config_id"] / (manifest["run_id"] + ".json")
        config = json.loads(result_path.read_text(encoding="utf-8"))["config"]
        for key, expected in config["settings"].items():
            actual = getattr(settings, key)
            if key in {"embedding_model", "chat_model"}:
                actual = actual if ":" in actual else actual + ":latest"
            elif key == "reranker_device" and actual == "auto":
                import torch
                actual = "cuda:0" if torch.cuda.is_available() else "cpu"
                expected = config["reranker_inference"]["device"]
            if actual != expected:
                return "custom_unverified"
        inference = config["reranker_inference"]
        if (settings.reranker_batch_size != inference["batch_size"] or
                settings.reranker_max_length != inference["max_length"] or
                settings.reranker_use_fp16 != inference["use_fp16"]):
            return "custom_unverified"
        device = settings.reranker_device
        if device == "auto":
            import torch
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
        if device != inference["device"]:
            return "custom_unverified"
        if environment_manifest() != json.loads((root / config["environment_manifest"]).read_text(encoding="utf-8")):
            return "custom_unverified"
        if model_digests(settings.ollama_base_url, {k: v["name"] for k, v in config["models"].items()}) != config["models"]:
            return "custom_unverified"
        return "acceptance_verified"
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError, httpx.HTTPError):
        return "custom_unverified"
