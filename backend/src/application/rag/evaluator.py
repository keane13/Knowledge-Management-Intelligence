"""
Evaluator – RAGAS metrics (Groq as LLM judge) + BERTScore.
Logs results directly to Arize Phoenix Cloud via OpenTelemetry spans.
"""
from __future__ import annotations

import logging
from pydantic import BaseModel
from ragas.metrics.collections import (
    Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall,
)
from ragas.llms import llm_factory
from ragas.embeddings import HuggingFaceEmbeddings
from openai import AsyncOpenAI
from bert_score import score as bert_score_fn

from src.infrastructure.config.configs import GROQ_API_KEY
from src.infrastructure.monitoring.phoenix_setup import get_tracer

logger = logging.getLogger(__name__)

_ragas_llm        = None
_ragas_embeddings = None


def _get_ragas_llm():
    global _ragas_llm
    if _ragas_llm is None:
        groq_client = AsyncOpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            max_retries=5,
        )
        _ragas_llm = llm_factory(model="llama-3.3-70b-versatile", client=groq_client)
    return _ragas_llm


def _get_ragas_embeddings():
    global _ragas_embeddings
    if _ragas_embeddings is None:
        _ragas_embeddings = HuggingFaceEmbeddings(
            model="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _ragas_embeddings


class ExperimentResult(BaseModel):
    faithfulness:      float
    answer_relevancy:  float
    context_precision: float
    context_recall:    float
    bert_score_f1:     float


async def run_ragas_evaluation(row) -> ExperimentResult:
    llm = _get_ragas_llm()
    emb = _get_ragas_embeddings()

    safe_input     = str(row.user_input)
    safe_response  = str(row.response) if row.response else "No answer provided."
    safe_contexts  = [str(c) for c in row.retrieved_contexts] if row.retrieved_contexts else ["No context available."]
    has_ref        = hasattr(row, 'reference') and bool(row.reference and str(row.reference).strip())
    safe_reference = str(row.reference) if has_ref else ""

    def extract_score(res):
        if res is None: return 0.0
        return float(getattr(res, 'value', res))

    # FIX: Buka span DULU, lalu hitung semua scores di dalamnya
    # supaya span masih aktif saat set_attribute dipanggil
    tracer = get_tracer("ragas_evaluator")
    with tracer.start_as_current_span("ragas_evaluation") as span:

        # Set metadata span di awal
        span.set_attribute("openinference.span.kind", "EVALUATOR")
        span.set_attribute("input.value",              safe_input)
        span.set_attribute("output.value",             safe_response)

        f_score = ar_score = cp_score = cr_score = bert_f1 = 0.0

        # ── Faithfulness ──────────────────────────────────────────────────────
        try:
            f_score = extract_score(
                await Faithfulness(llm=llm).ascore(
                    user_input=safe_input,
                    response=safe_response,
                    retrieved_contexts=safe_contexts,
                )
            )
        except Exception as e:
            logger.warning(f"Faithfulness failed: {e}")
        finally:
            span.set_attribute("eval.ragas.faithfulness", f_score)

        # ── Answer Relevancy ──────────────────────────────────────────────────
        try:
            ar_score = extract_score(
                await AnswerRelevancy(llm=llm, embeddings=emb).ascore(
                    user_input=safe_input,
                    response=safe_response,
                )
            )
        except Exception as e:
            logger.warning(f"Answer Relevancy failed: {e}")
        finally:
            span.set_attribute("eval.ragas.answer_relevancy", ar_score)

        # ── Context Precision & Recall (hanya jika ada ground_truth) ─────────
        if has_ref:
            try:
                cp_score = extract_score(
                    await ContextPrecision(llm=llm).ascore(
                        user_input=safe_input,
                        retrieved_contexts=safe_contexts,
                        reference=safe_reference,
                    )
                )
            except Exception as e:
                logger.warning(f"Context Precision failed: {e}")
            finally:
                span.set_attribute("eval.ragas.context_precision", cp_score)

            try:
                cr_score = extract_score(
                    await ContextRecall(llm=llm).ascore(
                        user_input=safe_input,
                        retrieved_contexts=safe_contexts,
                        reference=safe_reference,
                    )
                )
            except Exception as e:
                logger.warning(f"Context Recall failed: {e}")
            finally:
                span.set_attribute("eval.ragas.context_recall", cr_score)

        # ── BERTScore ─────────────────────────────────────────────────────────
        try:
            ref_text = safe_reference if has_ref else " ".join(safe_contexts)
            if ref_text:
                _, _, F1 = bert_score_fn(
                    cands=[safe_response],
                    refs=[ref_text],
                    model_type="bert-base-multilingual-cased",
                    lang="id",
                    verbose=False,
                )
                bert_f1 = round(float(F1[0]), 4)
        except Exception as e:
            logger.warning(f"BERTScore failed: {e}")
        finally:
            span.set_attribute("eval.bert_score_f1", bert_f1)

        # ── RAGAS F1 (harmonic mean faithfulness + answer_relevancy) ─────────
        ragas_f1 = (
            2 * f_score * ar_score / (f_score + ar_score)
            if (f_score + ar_score) > 0 else 0.0
        )
        span.set_attribute("eval.ragas.f1_score", round(ragas_f1, 4))

        # Log summary ke console untuk monitoring batch progress
        logger.info(
            f"RAGAS | faith={f_score:.3f} rel={ar_score:.3f} "
            f"prec={cp_score:.3f} rec={cr_score:.3f} "
            f"bert={bert_f1:.3f} f1={ragas_f1:.3f}"
        )

    # Return setelah span ditutup — nilai sudah tersimpan di Phoenix
    return ExperimentResult(
        faithfulness=f_score,
        answer_relevancy=ar_score,
        context_precision=cp_score,
        context_recall=cr_score,
        bert_score_f1=bert_f1,
    )