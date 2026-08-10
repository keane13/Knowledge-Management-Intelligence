"""
Evaluator – RAGAS metrics (Groq as LLM judge) + BERTScore.
Fully adapted to Ragas v0.4 Architecture (Stable Release).
"""
from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel
from ragas import experiment
from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
)
from ragas.llms import llm_factory
from ragas.embeddings import HuggingFaceEmbeddings
from openai import AsyncOpenAI
from bert_score import score as bert_score_fn

from src.infrastructure.config.configs import GROQ_API_KEY

logger = logging.getLogger(__name__)

_ragas_llm = None
_ragas_embeddings = None

def _get_ragas_llm():
    global _ragas_llm
    if _ragas_llm is None:
        groq_client = AsyncOpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            max_retries=5, 
        )
        _ragas_llm = llm_factory(model="llama-3.1-8b-instant", client=groq_client)
    return _ragas_llm

def _get_ragas_embeddings():
    global _ragas_embeddings
    if _ragas_embeddings is None:
        _ragas_embeddings = HuggingFaceEmbeddings(
            model="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _ragas_embeddings

class ExperimentResult(BaseModel):
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    bert_score_f1: float

@experiment(ExperimentResult)
async def run_ragas_evaluation(row) -> ExperimentResult:
    llm = _get_ragas_llm()
    emb = _get_ragas_embeddings()

    faithfulness_metric = Faithfulness(llm=llm)
    answer_relevancy_metric = AnswerRelevancy(llm=llm, embeddings=emb)

    f_score, ar_score, cp_score, cr_score = 0.0, 0.0, 0.0, 0.0

    # 1. Pastikan tipe data aman (casting eksplisit) untuk menghindari error "float has no len"
    safe_input = str(row.user_input)
    safe_response = str(row.response) if row.response else "No answer provided."
    safe_contexts = [str(c) for c in row.retrieved_contexts] if row.retrieved_contexts else ["No context available."]
    
    has_ref = hasattr(row, 'reference') and bool(row.reference and str(row.reference).strip())
    safe_reference = str(row.reference) if has_ref else ""

    # Helper function untuk mengekstrak nilai metrik
    def extract_score(res):
        if res is None: return 0.0
        return float(getattr(res, 'value', res))

    # 2. Faithfulness (Butuh input, response, dan contexts)
    try:
        f_res = await faithfulness_metric.ascore(
            user_input=safe_input,
            response=safe_response,
            retrieved_contexts=safe_contexts
        )
        f_score = extract_score(f_res)
    except Exception as e:
        logger.warning(f"Faithfulness failed: {e}")

    # 3. Answer Relevancy (Hanya butuh input dan response)
    try:
        ar_res = await answer_relevancy_metric.ascore(
            user_input=safe_input,
            response=safe_response
        )
        ar_score = extract_score(ar_res)
    except Exception as e:
        logger.warning(f"Answer Relevancy failed: {e}")

    if has_ref:
        # 4. Context Precision (Hanya butuh input, contexts, dan reference)
        try:
            cp_metric = ContextPrecision(llm=llm)
            cp_res = await cp_metric.ascore(
                user_input=safe_input,
                retrieved_contexts=safe_contexts,
                reference=safe_reference
            )
            cp_score = extract_score(cp_res)
        except Exception as e:
            logger.warning(f"Context Precision failed: {e}")

        # 5. Context Recall (Hanya butuh input, contexts, dan reference)
        try:
            cr_metric = ContextRecall(llm=llm)
            cr_res = await cr_metric.ascore(
                user_input=safe_input,
                retrieved_contexts=safe_contexts,
                reference=safe_reference
            )
            cr_score = extract_score(cr_res)
        except Exception as e:
            logger.warning(f"Context Recall failed: {e}")

    # 6. Hitung BERTScore
    bert_f1 = 0.0
    try:
        ref_text = safe_reference if has_ref else " ".join(safe_contexts)
        if ref_text:
            P, R, F1 = bert_score_fn(
                cands=[safe_response],
                refs=[ref_text],
                model_type="bert-base-multilingual-cased",
                lang="en",
                verbose=False,
            )
            bert_f1 = round(float(F1[0]), 4)
    except Exception as e:
        logger.warning(f"BERTScore failed: {e}")

    return ExperimentResult(
        faithfulness=f_score,
        answer_relevancy=ar_score,
        context_precision=cp_score,
        context_recall=cr_score,
        bert_score_f1=bert_f1
    )