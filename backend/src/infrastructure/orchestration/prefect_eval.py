import json
import os
import asyncio
from datetime import timedelta
from prefect import flow, task
from prefect.deployments import Deployment
from prefect.client.schemas.schedules import IntervalSchedule

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.application.rag.evaluator import run_ragas_evaluation

DATASET_PATH = "data/golden_eval_dataset.json"
OUTPUT_PATH = "data/hasil_eval.json"

@task(name="load_dataset")
def load_dataset() -> list:
    if not os.path.exists(DATASET_PATH):
        print(f"Dataset not found at {DATASET_PATH}")
        return []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@task(name="evaluate_row")
async def evaluate_row(row: dict) -> dict:
    try:
        result = await run_ragas_evaluation(row)
        return {
            "question": row.get("user_query"),
            "metrics": result.scores if hasattr(result, 'scores') else {}
        }
    except Exception as e:
        print(f"Error evaluating row: {e}")
        return {"question": row.get("user_query"), "error": str(e)}

@task(name="save_evaluation")
def save_evaluation(results: list):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    aggregated = {
        "timestamp": "now",
        "total_evaluations": len(results),
        "results": results
    }
    
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(aggregated, f, indent=4)
    print(f"Evaluation saved to {OUTPUT_PATH}")

@flow(name="ragas_evaluation_pipeline")
async def ragas_evaluation_pipeline():
    dataset = load_dataset()
    if not dataset:
        return
    
    dataset_to_evaluate = dataset[:5] 
    
    results = []
    for row in dataset_to_evaluate:
        res = await evaluate_row(row)
        results.append(res)
        
    save_evaluation(results)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "deploy":
        deployment = Deployment.build_from_flow(
            flow=ragas_evaluation_pipeline,
            name="Ragas-Eval-3-Days",
            schedule=IntervalSchedule(interval=timedelta(days=3)),
            work_pool_name="default-agent-pool"
        )
        deployment.apply()
        print("Deployment created. Start your worker with `prefect worker start --pool 'default-agent-pool'`")
    else:
        asyncio.run(ragas_evaluation_pipeline())
