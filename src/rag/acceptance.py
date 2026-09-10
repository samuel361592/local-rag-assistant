"""Reproducible acceptance identities and clean-worktree verification."""
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata
from pathlib import Path
import json
import platform
import re
import subprocess
import sys
import os
import site
import httpx
import rfc8785

from .retrieval_errors import RetrievalConfigError


def hash_file(path):
    checksum = sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def config_id(config):
    return sha256(rfc8785.dumps(config)).hexdigest()


def run_id(commit, config_hash):
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + commit[:12] + "_" + config_hash[:12]


def installed_distributions():
    result = {}
    for dist in metadata.distributions():
        name = re.sub(r"[-_.]+", "-", dist.metadata["Name"].lower())
        if name in result or not dist.version:
            raise RetrievalConfigError("依賴環境含重複名稱或缺少版本。")
        direct = dist.read_text("direct_url.json")
        if direct and json.loads(direct).get("dir_info", {}).get("editable"):
            raise RetrievalConfigError("Acceptance 不允許 editable install。")
        result[name] = dist.version
    return result


def environment_manifest():
    return {"schema": "acceptance-environment-v1", "python": platform.python_version(),
            "platform": f"{sys.platform}|{platform.machine().lower()}", "distributions": installed_distributions()}


def model_digests(base_url, models):
    response = httpx.get(base_url.rstrip("/") + "/api/tags", timeout=30)
    response.raise_for_status()
    result = {}
    for role, name in models.items():
        matches = [m for m in response.json()["models"] if m["name"] == name]
        if len(matches) != 1:
            raise RetrievalConfigError(f"Ollama 模型名稱必須唯一且包含 tag：{name}")
        value = matches[0].get("digest", "").removeprefix("sha256:").lower()
        if not re.fullmatch("[0-9a-f]{64}", value):
            raise RetrievalConfigError("Ollama 模型 digest 不合法。")
        result[role] = {"name": name, "digest": value}
    return result


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def safe_path(root, relative):
    if "\\" in relative or any(p in {".", "..", ""} for p in relative.split("/")) or Path(relative).is_absolute():
        raise RetrievalConfigError("Fingerprint 路徑不合法。")
    path = root / relative
    relative.encode("utf-8")
    if (any(parent.is_symlink() for parent in (path, *path.parents) if parent != root.parent)
            or not path.is_file() or not path.resolve().is_relative_to(root.resolve())):
        raise RetrievalConfigError(f"Fingerprint 缺少普通檔案：{relative}")
    return path


def fingerprint(root, dataset_path, config_path, config, dataset, digests):
    tracked = git(root, "ls-files", "-z").decode().split("\0")
    names = {p for p in tracked if p.startswith("src/") and p.endswith(".py")}
    imported = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, "__file__", None)}
    names |= {p for p in tracked if p.startswith("evaluation/") and p.endswith(".py") and (root / p).resolve() in imported}
    names |= {"scripts/evaluate_retrieval.py", "src/rag/tokenizer_userdict.txt", "requirements.txt", ".gitattributes",
              config["environment_manifest"], dataset_path, config_path}
    names |= {source["path"] for source in dataset["sources"]}
    files = {p: hash_file(safe_path(root, p)) for p in sorted(names)}
    obj = {"schema": "pipeline-fingerprint-v2", "files": files,
           "models": {**digests, "reranker": config["reranker_identity"]},
           "runtime": {"python": platform.python_version(), "rank_bm25": metadata.version("rank-bm25"),
                       "jieba": metadata.version("jieba"),
                       "environment_manifest_sha256": files[config["environment_manifest"]],
                       "installed_distributions_sha256": config_id(installed_distributions()),
                       "retrieval_execution_mode": config["retrieval_execution_mode"]}}
    return config_id(obj), obj


def worktree_check(root, commit, fingerprint_obj, dataset):
    if git(root, "rev-parse", "HEAD").decode().strip() != commit:
        raise RetrievalConfigError("INVALID_WORKTREE_CHANGED")
    tracked = set(git(root, "ls-files", "-z").decode().split("\0"))
    sources = {s["path"]: s["sha256"] for s in dataset["sources"]}
    for name, checksum in fingerprint_obj["files"].items():
        path = safe_path(root, name)
        if name in tracked:
            if path.read_bytes() != git(root, "show", f"{commit}:{name}"):
                raise RetrievalConfigError(f"INVALID_WORKTREE_CHANGED: {name}")
        elif sources.get(name) != checksum:
            raise RetrievalConfigError(f"未提交的 Acceptance 輸入：{name}")
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching", "-z")
    for record in status.decode().split("\0"):
        name = record[3:]
        if not name or name.startswith("evaluation/results/") or name in sources:
            continue
        if name.startswith(("src/", "evaluation/")) or name == "scripts/evaluate_retrieval.py":
            raise RetrievalConfigError(f"Acceptance 工作目錄不乾淨：{name}")
    for module in list(sys.modules.values()):
        file = getattr(module, "__file__", None)
        if file and Path(file).resolve().is_relative_to(root.resolve()):
            name = Path(file).resolve().relative_to(root.resolve()).as_posix()
            if name.endswith((".py", ".pyc")) and name not in fingerprint_obj["files"]:
                raise RetrievalConfigError(f"INVALID_IMPORT_SCOPE: {name}")
    for name, checksum in sources.items():
        if hash_file(root / name) != checksum:
            raise RetrievalConfigError(f"語料雜湊不符：{name}")


def verify_environment(root, config):
    expected = json.loads((root / config["environment_manifest"]).read_text(encoding="utf-8"))
    actual = environment_manifest()
    if actual != expected:
        raise RetrievalConfigError("實際依賴環境與 Acceptance Manifest 不符。")
    if Path(sys.prefix).resolve().is_relative_to(root.resolve()):
        raise RetrievalConfigError("Acceptance 必須使用 Repository 外的隔離 Python 環境。")
    if not sys.dont_write_bytecode:
        raise RetrievalConfigError("Acceptance 必須使用 python -B。")
    if site.ENABLE_USER_SITE or os.environ.get("PYTHONPATH"):
        raise RetrievalConfigError("Acceptance 不允許 user site-packages 或未宣告 PYTHONPATH。")
    allowed_roots = [Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve(), root.resolve()]
    for entry in sys.path:
        path = Path(entry or os.getcwd()).resolve()
        if not any(path.is_relative_to(allowed) for allowed in allowed_roots):
            raise RetrievalConfigError(f"Acceptance import path 超出宣告範圍：{path}")
    return actual


def write_result(path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def verify_promotion(root, manifest_path="evaluation/releases/hybrid-default.json"):
    """Fail closed; only a verified acceptance can authorize a release default."""
    manifest = json.loads((root / manifest_path).read_text(encoding="utf-8"))
    commit = manifest["evaluated_commit"]
    subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", commit, "HEAD"], check=True)
    result_path = root / "evaluation/results" / manifest["dataset_version"] / manifest["config_id"] / (manifest["run_id"] + ".json")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if (result["run_purpose"] != "acceptance" or result["gate"]["status"] != "PASSED"
            or result["evaluated_commit"] != commit
            or result["pipeline_fingerprint"] != manifest["pipeline_fingerprint"]):
        raise RetrievalConfigError("發布 Manifest 沒有有效 Acceptance。")
    for name, checksum in result["fingerprint_manifest"]["files"].items():
        if hash_file(safe_path(root, name)) != checksum:
            raise RetrievalConfigError("STALE_ACCEPTANCE")
    changed = git(root, "diff", "--name-only", commit, "HEAD").decode().splitlines()
    for name in changed:
        if name == "src/rag/release_defaults.json":
            old = json.loads(git(root, "show", f"{commit}:{name}"))
            new = json.loads((root / name).read_text(encoding="utf-8"))
            if set(new) != {"schema_version", "hybrid_search_enabled"} or new["schema_version"] != old["schema_version"] or new["hybrid_search_enabled"] is not True:
                raise RetrievalConfigError("Promotion 修改了非允許的發布設定。")
        elif name == ".env.example":
            old = git(root, "show", f"{commit}:{name}").decode()
            new = (root / name).read_text(encoding="utf-8")
            if old.replace("HYBRID_SEARCH_ENABLED=false", "HYBRID_SEARCH_ENABLED=true") != new:
                raise RetrievalConfigError("Promotion 修改了其他環境設定。")
        elif name == manifest_path or (root / name) == result_path:
            continue
        elif name == "README.md" or name.startswith("docs/") and name.endswith(".md"):
            continue
        else:
            raise RetrievalConfigError(f"STALE_ACCEPTANCE: {name}")
    return manifest
