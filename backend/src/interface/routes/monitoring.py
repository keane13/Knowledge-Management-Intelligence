import os
import json
import math
import pandas as pd
from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse
from src.application.rag.vectorstore import get_weaviate_client
from src.infrastructure.llm.llm import generate_answer, DEFAULT_TEXT_MODEL
from src.infrastructure.config.configs import DOCS_PATH
from pathlib import Path

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

@router.get("/dashboard/metrics")
def get_dashboard_metrics():
    def safe_float(val, default=0.0):
        try:
            f = float(val)
            return default if (math.isnan(f) or math.isinf(f)) else f
        except:
            return default

    metrics = {
        "avg_retrieval_latency": 0.0,
        "avg_rerank_latency": 0.0,
        "avg_generation_latency": 0.0,
        "avg_bert_score": 0.0,
        "ragas_score": 0.0,
        "total_documents": 0,
        "total_cost": 0.0,
        "debug_status": "Starting..."
    }

    if os.path.exists(DOCS_PATH):
        base_path = Path(DOCS_PATH)
        metrics["total_documents"] = sum(1 for p in base_path.rglob('*') if p.is_file())

    try:
        api_key = os.getenv("PHOENIX_API_KEY")
        if not api_key:
            metrics["debug_status"] = "ERROR: PHOENIX_API_KEY is not set."
        else:
            from phoenix.client import Client
            client = Client(
                base_url="https://app.phoenix.arize.com",
                api_key=api_key,
            )

            df = client.spans.get_spans_dataframe(
                project_identifier="rag_pro",
                limit=50,
            )

            if df is None or df.empty:
                metrics["debug_status"] = "SUCCESS: Connected but DataFrame is EMPTY."
            else:
                metrics["debug_status"] = f"SUCCESS: Fetched {len(df)} spans."

                # ── Duration ──────────────────────────────────────────────────────────
                if 'latency_ms' in df.columns:
                    df['duration_sec'] = pd.to_numeric(df['latency_ms'], errors='coerce') / 1000.0
                else:
                    df['start_time']   = pd.to_datetime(df['start_time'], errors='coerce')
                    df['end_time']     = pd.to_datetime(df['end_time'],   errors='coerce')
                    df['duration_sec'] = (df['end_time'] - df['start_time']).dt.total_seconds()

                # ── Retrieval & Rerank (use their own spans) ──────────────────────────
                retrieval_df = df[df['name'].str.lower() == 'retrieval']
                if not retrieval_df.empty:
                    metrics["avg_retrieval_latency"] = safe_float(
                        retrieval_df['duration_sec'].dropna().mean()
                    )

                rerank_df = df[df['name'].str.lower() == 'rerank']
                if not rerank_df.empty:
                    metrics["avg_rerank_latency"] = safe_float(
                        rerank_df['duration_sec'].dropna().mean()
                    )

                # ── Generation: use "Completions" (actual LLM call), NOT "generation" ─
                completions_df = df[df['name'] == 'Completions']
                if not completions_df.empty:
                    metrics["avg_generation_latency"] = safe_float(
                        completions_df['duration_sec'].dropna().mean()
                    )

                # ── Cost: token count from Completions spans ──────────────────────────
                for cost_col in [
                    'attributes.llm.usage.total_cost',
                    'attributes.llm.token.count.completion',
                    'attributes.llm.token.count.total',
                ]:
                    if cost_col in df.columns:
                        val = completions_df[cost_col].dropna().astype(float).sum()
                        metrics["total_cost"] = safe_float(val)
                        if metrics["total_cost"] > 0:
                            break

                # ── RAGAS Score ───────────────────────────────────────────────────────
                ragas_col = 'attributes.eval.ragas.f1_score'
                if ragas_col in df.columns:
                    val = df[ragas_col].dropna().astype(float).mean()
                    metrics["avg_bert_score"] = safe_float(val)

    except Exception as e:
        metrics["debug_status"] = f"ERROR: {type(e).__name__}: {str(e)}"

    # Provide default RAGAS metrics structure
    metrics["ragas_metrics"] = {
        "faithfulness": 0.0,
        "answer_relevancy": 0.0,
        "context_precision": 0.0,
        "context_recall": 0.0,
        "semantic_accuracy": 0.0
    }

    eval_path = os.path.join(DOCS_PATH, "..", "hasil_eval.json")
    if not os.path.exists(eval_path):
        # Fix: Need to go up 4 levels to get to rag_pro_v3 from routes directory
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        eval_path = os.path.join(BASE_DIR, "data", "hasil_eval.json")
    
    if os.path.exists(eval_path):
        try:
            with open(eval_path, "r") as f:
                eval_data = json.load(f)
                
                if metrics["avg_bert_score"] == 0.0:
                    metrics["avg_bert_score"] = safe_float(eval_data.get("summary_metrics", {}).get("overall_rag_score", 0.0))
                
                gen_qual = eval_data.get("generation_quality", {})
                ret_perf = eval_data.get("retrieval_performance", {})
                
                metrics["ragas_metrics"] = {
                    "faithfulness": safe_float(gen_qual.get("faithfulness", {}).get("score", 0.0)),
                    "answer_relevancy": safe_float(gen_qual.get("answer_relevancy", {}).get("score", 0.0)),
                    "context_precision": safe_float(ret_perf.get("context_precision", {}).get("score", 0.0)),
                    "context_recall": safe_float(ret_perf.get("context_recall", {}).get("score", 0.0)),
                    "semantic_accuracy": safe_float(gen_qual.get("semantic_accuracy_bert", {}).get("score", 0.0))
                }
        except Exception:
            pass

    return metrics

@router.get("/dashboard/debug")
def get_debug_spans():
    """Temporary debug endpoint - shows raw Phoenix span data."""
    from phoenix.client import Client

    try:
        client = Client(
            base_url="https://app.phoenix.arize.com",
            api_key=os.getenv("PHOENIX_API_KEY"),
        )

        df = client.spans.get_spans_dataframe(
            project_identifier="rag_pro",
            limit=20,
        )

        if df is None or df.empty:
            return {"error": "Empty dataframe"}

        target_spans = df[df['name'].str.lower().isin(['retrieval', 'rerank', 'generation'])]

        return {
            "total_spans_fetched": len(df),
            "all_column_names": list(df.columns),
            "target_span_count": len(target_spans),
            "target_spans_raw": target_spans.to_dict(orient='records'),
            "all_span_names": df['name'].unique().tolist(),
        }

    except Exception as e:
        import traceback
        return {"error": str(e), "trace": traceback.format_exc()}
