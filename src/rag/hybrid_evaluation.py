"""Four-arm, shared-computation benchmark with exact quality gates."""
from collections import Counter
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction
from hashlib import sha256
from math import ceil
import random
from time import perf_counter_ns

from .hybrid_retriever import ranked_documents, reciprocal_rank_fusion
from .reranker import rerank_documents
from .vector_store import similarity_search
from .chunk_identity import validate_candidates
from .retrieval_errors import RetrievalInvariantError, RetrievalConfigError

GROUPS = ("DENSE_RAW", "CURRENT_BASELINE", "HYBRID_RRF", "TARGET")
CUTOFFS = (1, 3, 5, 8, 20)


def gold_matches(doc, target):
    m, loc = doc.metadata, target["location"]
    if m["source_content_sha256"] != target["source_content_sha256"]:
        return False
    if m["source_type"] == "excel":
        if not {"sheet_name", "row_start", "row_end"} <= loc.keys():
            raise RetrievalConfigError("Excel Gold 必須包含工作表與列區間。")
        if not (m["sheet_name"] == loc["sheet_name"] and m["row_start"] <= loc["row_start"] <= loc["row_end"] <= m["row_end"]):
            return False
    elif any(m.get(k) != v for k, v in loc.items()):
        return False
    return target["expected_text"] in doc.page_content


def preflight_gold(dataset, registry):
    questions = dataset["questions"]
    if Counter(q["category"] for q in questions) != {
            "semantic_paraphrase": 20, "exact_term": 10, "exact_identifier": 10, "mixed_semantic_exact": 10}:
        raise RetrievalConfigError("Golden Dataset 題型或題數不符合規格。")
    if len({q["id"] for q in questions}) != 50:
        raise RetrievalConfigError("Golden Dataset ID 重複。")
    gold = {}
    for question in questions:
        if not question["question"].strip() or not question["gold_targets"]:
            raise RetrievalConfigError("Golden Dataset 問題或 Gold 不可為空。")
        ids = set()
        for target in question["gold_targets"]:
            found = [key for key, doc in registry.items() if gold_matches(doc, target)]
            if len(found) != 1:
                raise RetrievalConfigError(f"Gold {question['id']} 必須唯一命中，實際 {len(found)} 筆。")
            ids.update(found)
        gold[question["id"]] = ids
    return gold


def exact_metrics(rows):
    n = len(rows)
    return {**{f"hit_rate@{k}": Fraction(sum(r is not None and r <= k for r in rows), n) for k in CUTOFFS},
            "mrr@20": sum((Fraction(1, r) if r else Fraction() for r in rows), Fraction()) / n}


def fraction_json(value):
    return {"numerator": value.numerator, "denominator": value.denominator,
            "decimal": str((Decimal(value.numerator) / Decimal(value.denominator)).quantize(
                Decimal("0.00000001"), rounding=ROUND_HALF_EVEN))}


def percentile(values, p):
    return sorted(values)[ceil(len(values) * p)-1]


def quality_gate(metrics):
    b, t = metrics["CURRENT_BASELINE"], metrics["TARGET"]
    checks = {
        "overall_mrr": t["all"]["mrr@20"] >= b["all"]["mrr@20"],
        "overall_hit8": t["all"]["hit_rate@8"] >= b["all"]["hit_rate@8"],
        "semantic": t["semantic_paraphrase"]["hit_rate@8"] >= b["semantic_paraphrase"]["hit_rate@8"] - Fraction(1, 20),
    }
    exact_b, exact_t = b["exact_identifier"], t["exact_identifier"]
    checks["exact"] = (exact_t["hit_rate@5"] >= exact_b["hit_rate@5"] + Fraction(1, 10)
                       if exact_b["hit_rate@5"] < 1 else
                       exact_t["hit_rate@5"] == 1 and exact_t["mrr@20"] >= exact_b["mrr@20"])
    selected = [("all", "mrr@20"), ("all", "hit_rate@8"),
                ("exact_identifier", "mrr@20"), ("mixed_semantic_exact", "hit_rate@5")]
    ceiling = all(b[c][m] == 1 for c, m in selected)
    checks["improvement"] = (all(t[c][m] == 1 for c, m in selected) if ceiling
                             else any(t[c][m] > b[c][m] for c, m in selected))
    status = ("CEILING_NON_INFERIOR" if ceiling else "PASSED") if all(checks.values()) else "FAILED"
    return {"status": status, "checks": checks}


def run_benchmark(dataset, registry, vector, bm25, reranker, settings, *, progress=None):
    if min(settings.retrieval_top_k, settings.bm25_top_k, settings.fusion_top_k) < 20:
        raise RetrievalConfigError("Evaluation 候選深度不得小於 20。")
    gold = preflight_gold(dataset, registry)
    questions = {q["id"]: q for q in dataset["questions"]}
    rows, signatures = [], {}
    def timed(fn):
        start = perf_counter_ns()
        value = fn()
        return value, perf_counter_ns() - start
    def dense_search(query):
        docs = similarity_search(vector, query, settings.retrieval_top_k)
        validate_candidates(docs, registry)
        return [r.document for r in ranked_documents(docs)]
    for trial in range(-1, 5):
        order = list(questions)
        if trial >= 0:
            random.Random(20260908 + trial).shuffle(order)
        for qid in order:
            if progress:
                progress(f"{'warmup' if trial == -1 else f'trial {trial+1}'}: {qid}")
            query = questions[qid]["question"].strip()
            dense, dt = timed(lambda: dense_search(query))
            dense_rank = ranked_documents(dense)
            dense = [r.document for r in dense_rank]
            sparse, bt = timed(lambda: bm25.search(query, settings.bm25_top_k))
            validate_candidates([r.document for r in sparse], registry)
            baseline, brt = timed(lambda: rerank_documents(query, dense, reranker, 20))
            fused, ft = timed(lambda: reciprocal_rank_fusion([dense_rank, sparse], settings.rrf_k, settings.fusion_top_k))
            target, trt = timed(lambda: rerank_documents(query, fused, reranker, 20))
            if trial < 0:
                continue
            rankings = dict(zip(GROUPS, (dense[:20], baseline, fused[:20], target)))
            durations = dict(zip(GROUPS, (dt, dt+brt, dt+bt+ft, dt+bt+ft+trt)))
            for group, docs in rankings.items():
                ids = [doc.metadata["chunk_id"] for doc in docs]
                signature = sha256("\0".join(ids).encode()).hexdigest()
                signatures.setdefault((qid, group), set()).add(signature)
                rows.append({"trial": trial, "question_id": qid, "category": questions[qid]["category"],
                             "group": group, "chunk_ids": ids, "ranking_signature": signature,
                             "rank": next((i for i, key in enumerate(ids, 1) if key in gold[qid]), None),
                             "dense_hit": bool(gold[qid] & {r.chunk_id for r in dense_rank}),
                             "bm25_hit": bool(gold[qid] & {r.chunk_id for r in sparse}),
                             "fusion_hit": bool(gold[qid] & {d.metadata["chunk_id"] for d in fused}),
                             "duration_ns": durations[group], "dense_duration_ns": dt,
                             "bm25_duration_ns": bt, "rrf_duration_ns": ft,
                             "reranker_duration_ns": brt if group == "CURRENT_BASELINE" else trt if group == "TARGET" else 0,
                             "dense_candidate_count": len(dense), "baseline_reranker_input_count": len(dense),
                             "fused_candidate_count": len(fused), "target_reranker_input_count": len(fused)})
    categories = ["all", *sorted({q["category"] for q in questions.values()})]
    metrics = {g: {c: exact_metrics([r["rank"] for r in rows if r["group"] == g and
                        (c == "all" or r["category"] == c)]) for c in categories} for g in GROUPS}
    trial_metrics = {str(i): {g: {c: exact_metrics([r["rank"] for r in rows if r["trial"] == i and
                    r["group"] == g and (c == "all" or r["category"] == c)]) for c in categories}
                    for g in GROUPS} for i in range(5)}
    gate = quality_gate(metrics)
    if any(len(s) != 1 for s in signatures.values()):
        gate = {"status": "NON_DETERMINISTIC", "checks": gate["checks"]}
    elif any(trial_metrics[str(i)] != metrics for i in range(5)):
        raise RetrievalInvariantError("Ranking 相同但 Trial 聚合指標不同。")
    latency = {g: {f"p{int(p*100)}_ns": percentile([r["duration_ns"] for r in rows if r["group"] == g], p)
                   for p in (.5, .95)} for g in GROUPS}
    extra = percentile([r["bm25_duration_ns"] + r["rrf_duration_ns"] for r in rows if r["group"] == "TARGET"], .95)
    return {"gate": gate, "rows": rows, "latency": latency, "extra_p95_ns": extra,
            "trial_metrics": {i: {g: {c: {m: fraction_json(v) for m, v in values.items()}
                              for c, values in cats.items()} for g, cats in groups.items()}
                              for i, groups in trial_metrics.items()},
            "performance_warning": extra >= 100_000_000,
            "metrics": {g: {c: {m: fraction_json(v) for m, v in values.items()} for c, values in cats.items()}
                        for g, cats in metrics.items()},
            "baseline_vs_dense_delta": {c: {m: fraction_json(v - metrics["DENSE_RAW"][c][m]) for m, v in values.items()}
                                        for c, values in metrics["CURRENT_BASELINE"].items()},
            "deltas": {g: {c: {m: fraction_json(v - metrics["CURRENT_BASELINE"][c][m]) for m, v in values.items()}
                           for c, values in metrics[g].items()} for g in ("HYBRID_RRF", "TARGET")}}
