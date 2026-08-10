# batch_eval.py

from src.infrastructure.monitoring.phoenix_setup import setup_phoenix
setup_phoenix()

import sys, os, json, asyncio
import pandas as pd
from dataclasses import dataclass
from typing import List

from src.application.rag.evaluator import run_ragas_evaluation
from src.application.rag.pipeline import run_rag  # pipeline asli

@dataclass
class EvalRow:
    user_input: str
    response: str
    retrieved_contexts: List[str]
    reference: str

def main():
    print("Loading test data...")
    try:
         with open("data/ragas_eval.jsonl") as f:
            content = f.read().strip()
    
    # Auto-detect format
            if content.startswith("["):
        # Format JSON array biasa
                 data = json.loads(content)
            else:
        # Format JSONL sejati (satu object per baris)
                 data = [json.loads(line) for line in content.splitlines() if line.strip()]
    except FileNotFoundError:
        print("❌ Test data not found at data/ragas_eval.json")
        return

    # ── Fase 1: Generation via pipeline asli ─────────────────────────────────
    print("Running RAG pipeline generation...")
    dataset_records = []

    for item in data:
        question     = item["question"]
        ground_truth = item.get("ground_truth", "")
        print(f"➡ [{len(dataset_records)+1}/{len(data)}] {question[:60]}...")

        try:
            # Pipeline return trace_data dict (bukan streaming)
            trace_data = run_rag(
                question=question,
                stream=False,
                mode="fast",
            )

            # FIX: Unpack dari trace_data dict langsung
            answer        = trace_data.get("answer", "")
            contexts_list = trace_data.get("contexts", [])  # sudah List[str] dari pipeline

            if not answer:
                print(f"  ⚠️ Empty answer for: {question}")
            if not contexts_list:
                print(f"  ⚠️ Empty contexts for: {question} — check Weaviate retrieval")

        except Exception as e:
            print(f"  ❌ run_rag failed: {e}")
            answer        = ""
            contexts_list = []

        dataset_records.append(EvalRow(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts_list,  # ← langsung dari Weaviate via pipeline
            reference=ground_truth,
        ))

    # ── Fase 2: Sequential RAGAS Evaluation ──────────────────────────────────
    print(f"\nRunning RAGAS Evaluation for {len(dataset_records)} records...")

    async def evaluate_sequentially(records: List[EvalRow]):
        results = []
        for i, row in enumerate(records):
            print(f"  [Evaluating {i+1}/{len(records)}] {row.user_input[:50]}...")
            res = await run_ragas_evaluation(row)
            results.append(res)
            if i < len(records) - 1:
                await asyncio.sleep(4)  # hindari rate limit Groq
        return results

    exp_results = asyncio.run(evaluate_sequentially(dataset_records))

    # ── Fase 3: Simpan hasil ──────────────────────────────────────────────────
    records = []
    for i, row in enumerate(dataset_records):
        res = exp_results[i]
        records.append({
            "question":          row.user_input,
            "answer":            row.response,
            "ground_truth":      row.reference,
            "contexts":          " | ".join(row.retrieved_contexts),
            "faithfulness":      res.faithfulness,
            "answer_relevancy":  res.answer_relevancy,
            "context_precision": res.context_precision,
            "context_recall":    res.context_recall,
            "bert_score_f1":     res.bert_score_f1,
        })

    df = pd.DataFrame(records)

    summary_metrics = {
        "avg_faithfulness":      df["faithfulness"].mean(),
        "avg_answer_relevancy":  df["answer_relevancy"].mean(),
        "avg_context_precision": df["context_precision"].mean(),
        "avg_context_recall":    df["context_recall"].mean(),
        "avg_bert_score_f1":     df["bert_score_f1"].mean(),
    }

    out_path = "evaluation/results.csv"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)

    print(f"\n✅ Evaluation complete. Results → {out_path}")
    print("\n=== Aggregate Metrics ===")
    for k, v in summary_metrics.items():
        print(f"  {k}: {v:.4f}")

if __name__ == "__main__":
    main()