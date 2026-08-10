import mlflow
import pandas as pd

mlflow.set_tracking_uri("file:./mlruns")
experiment = mlflow.get_experiment_by_name("RAG_System_Evaluation")
if experiment:
    df = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    
    # Filter for runs that have the bert_score metric
    if 'metrics.bert_score_f1' in df.columns:
        # Find the run with score near 0.816
        target_runs = df[df['metrics.bert_score_f1'].notna()]
        print(f"Found {len(target_runs)} runs with bert_score_f1.")
        
        with open("mlflow_batch_output.txt", "w") as f:
            for _, run in target_runs.iterrows():
                f.write(f"Run ID: {run['run_id']}\n")
                if 'tags.mlflow.runName' in run:
                   f.write(f"Run Name: {run['tags.mlflow.runName']}\n")
                f.write(f"BERT Score F1: {run['metrics.bert_score_f1']}\n")
                if 'metrics.latency' in run:
                   f.write(f"Latency: {run['metrics.latency']}\n")
                f.write("-" * 20 + "\n")
    else:
        print("No bert_score_f1 metric column found.")
        print(df.columns)
else:
    print("Experiment not found")
