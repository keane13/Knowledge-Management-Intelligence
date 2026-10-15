import os
import json
import math
import time
from datetime import datetime
import requests
from fastapi import APIRouter, Response, Depends
from fastapi.responses import RedirectResponse
from src.application.rag.vectorstore import get_weaviate_client
from src.infrastructure.llm.llm import generate_answer, DEFAULT_TEXT_MODEL
from src.infrastructure.config.configs import DOCS_PATH
from pathlib import Path
from src.infrastructure.auth import get_current_user

router = APIRouter(tags=["Monitoring"])

@router.get("/monitoring")
def phoenix_dashboard():
    """Redirect to Arize Phoenix local dashboard (http://localhost:6006)."""
    return RedirectResponse(url="http://localhost:6006")

@router.get("/health")
def health_check():
    health_status = {"status": "ok", "weaviate": "unknown", "llm": "unknown"}
    try:
        client = get_weaviate_client()
        if client.is_ready():
            health_status["weaviate"] = "ok"
        else:
            health_status["weaviate"] = "error"
    except Exception as e:
        health_status["weaviate"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        
    try:
        # Minimal LLM ping
        ans = generate_answer([{"role": "user", "content": "Reply 'OK'"}], stream=False, model_key=DEFAULT_TEXT_MODEL)
        health_status["llm"] = "ok"
    except Exception as e:
        health_status["llm"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        
    if health_status["status"] == "degraded":
        return Response(content=json.dumps(health_status), media_type="application/json", status_code=503)
        
    return health_status

# ── Dashboard ────────────────────────────────────────────────────────────────
# Latencies come from Phoenix spans (cloud or self-hosted) via its REST API; RAGAS scores come
# from the last batch evaluation written to data/hasil_eval.json by the evaluation pipeline.

PHOENIX_PROJECT = os.getenv("PHOENIX_PROJECT_NAME", "rag_pro")
EVAL_RESULTS_PATH = Path(__file__).resolve().parents[3] / "data" / "hasil_eval.json"
_METRICS_TTL_SEC = 60
_metrics_cache = {"at": 0.0, "value": None}


def _phoenix_api():
    """Base URL + auth headers for the Phoenix REST API (derived from the OTLP collector endpoint)."""
    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "").rstrip("/")
    if endpoint.endswith("/v1/traces"):
        endpoint = endpoint[: -len("/v1/traces")]
    api_key = os.getenv("PHOENIX_API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    return endpoint, headers


def _fetch_spans(base: str, headers: dict, limit: int = 100, **filters) -> list:
    params = {"limit": limit, **filters}
    resp = requests.get(f"{base}/v1/projects/{PHOENIX_PROJECT}/spans", headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("data", [])


def _span_seconds(span: dict):
    try:
        start = datetime.fromisoformat(span["start_time"])
        end = datetime.fromisoformat(span["end_time"])
        return (end - start).total_seconds()
    except (KeyError, TypeError, ValueError):
        return None


def _avg_seconds(spans: list) -> float:
    durations = [d for d in (_span_seconds(s) for s in spans) if d is not None and d >= 0]
    return round(sum(durations) / len(durations), 4) if durations else 0.0


def _count_documents() -> int:
    """Documents in the knowledge bucket (source of truth on Cloud Run); local folder as fallback."""
    try:
        from src.interface.routes.documents import _gcs_client, GCS_BUCKET_NAME
        return sum(1 for b in _gcs_client().bucket(GCS_BUCKET_NAME).list_blobs() if not b.name.endswith("/"))
    except Exception as e:
        print(f"GCS document count failed, using local folder: {e}")
    if os.path.exists(DOCS_PATH):
        return sum(1 for p in Path(DOCS_PATH).rglob("*") if p.is_file())
    return 0


def _safe_float(val, default=0.0):
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return default


@router.get("/dashboard/metrics")
def get_dashboard_metrics():
    now = time.time()
    if _metrics_cache["value"] is not None and now - _metrics_cache["at"] < _METRICS_TTL_SEC:
        return _metrics_cache["value"]

    metrics = {
        "avg_retrieval_latency": 0.0,
        "avg_rerank_latency": 0.0,
        "avg_generation_latency": 0.0,
        "avg_bert_score": 0.0,
        "ragas_score": 0.0,
        "total_documents": _count_documents(),
        "total_cost": 0.0,
        # Streamed LLM calls do not report token usage, so cost can't be computed from traces
        "cost_available": False,
        "spans_sampled": 0,
        "last_trace_at": None,
        "debug_status": "Starting...",
        "ragas_metrics": {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "semantic_accuracy": 0.0,
        },
        "eval_date": None,
        "eval_samples": 0,
    }

    # ── Latencies from Phoenix traces ────────────────────────────────────────
    base, headers = _phoenix_api()
    if not base:
        metrics["debug_status"] = "ERROR: PHOENIX_COLLECTOR_ENDPOINT is not set."
    else:
        try:
            retrieval = _fetch_spans(base, headers, name="retrieval")
            rerank = _fetch_spans(base, headers, name="rerank")
            # The "generation" span only builds the prompt; the LLM call itself is the LLM-kind span
            llm = _fetch_spans(base, headers, span_kind="LLM")
            metrics["avg_retrieval_latency"] = _avg_seconds(retrieval)
            metrics["avg_rerank_latency"] = _avg_seconds(rerank)
            metrics["avg_generation_latency"] = _avg_seconds(llm)
            sampled = retrieval + rerank + llm
            metrics["spans_sampled"] = len(sampled)
            metrics["last_trace_at"] = max((s.get("start_time") for s in sampled if s.get("start_time")), default=None)
            metrics["debug_status"] = (
                f"SUCCESS: {len(retrieval)} retrieval, {len(rerank)} rerank, {len(llm)} LLM spans from Phoenix"
                if sampled else "SUCCESS: Connected to Phoenix but no RAG spans recorded yet."
            )
        except Exception as e:
            metrics["debug_status"] = f"ERROR: {type(e).__name__}: {str(e)[:200]}"

    # ── RAGAS scores from the last batch evaluation ──────────────────────────
    if EVAL_RESULTS_PATH.exists():
        try:
            eval_data = json.loads(EVAL_RESULTS_PATH.read_text(encoding="utf-8"))
            summary = eval_data.get("summary_metrics", {})
            gen_qual = eval_data.get("generation_quality", {})
            ret_perf = eval_data.get("retrieval_performance", {})
            overall = _safe_float(summary.get("overall_rag_score", 0.0))
            metrics["avg_bert_score"] = overall
            metrics["ragas_score"] = overall
            metrics["eval_date"] = eval_data.get("evaluation_date")
            metrics["eval_samples"] = int(summary.get("total_samples") or 0)
            metrics["ragas_metrics"] = {
                "faithfulness": _safe_float(gen_qual.get("faithfulness", {}).get("score", 0.0)),
                "answer_relevancy": _safe_float(gen_qual.get("answer_relevancy", {}).get("score", 0.0)),
                "context_precision": _safe_float(ret_perf.get("context_precision", {}).get("score", 0.0)),
                "context_recall": _safe_float(ret_perf.get("context_recall", {}).get("score", 0.0)),
                "semantic_accuracy": _safe_float(gen_qual.get("semantic_accuracy_bert", {}).get("score", 0.0)),
            }
        except Exception as e:
            print(f"Failed to read evaluation results: {e}")

    _metrics_cache.update(at=now, value=metrics)
    return metrics


@router.get("/dashboard/debug")
def get_debug_spans(current_user: str = Depends(get_current_user)):
    """Raw Phoenix span sample for troubleshooting the dashboard (login required)."""
    base, headers = _phoenix_api()
    try:
        spans = _fetch_spans(base, headers, limit=50)
        names = sorted({s.get("name") for s in spans})
        return {
            "phoenix_project": PHOENIX_PROJECT,
            "total_spans_fetched": len(spans),
            "all_span_names": names,
            "newest_span_at": max((s.get("start_time") for s in spans if s.get("start_time")), default=None),
            "sample": spans[:3],
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
