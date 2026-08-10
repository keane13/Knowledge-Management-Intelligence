import mlflow
import pandas as pd

mlflow.set_tracking_uri("file:./mlruns")
experiments = mlflow.search_experiments()
with open("mlflow_dump.txt", "w") as f:
    for exp in experiments:
        f.write(f"Experiment: {exp.name}\n")
        df = mlflow.search_runs(experiment_ids=[exp.experiment_id])
        if not df.empty:
            metric_cols = [c for c in df.columns if c.startswith('metrics.')]
            f.write(f"  Runs: {len(df)}\n")
            f.write(f"  Metrics: {metric_cols}\n")
            for _, run in df.iterrows():
                if 'tags.mlflow.runName' in run and 'Batch' in str(run['tags.mlflow.runName']):
                    f.write(f"  Batch Run found: {run['tags.mlflow.runName']}\n")
                    f.write(f"    {run[metric_cols].to_dict()}\n")
                if 'metrics.bert_score_f1' in run and pd.notna(run['metrics.bert_score_f1']):
                    f.write(f"    bert_score_f1: {run['metrics.bert_score_f1']} (Run Name: {run.get('tags.mlflow.runName', 'None')})\n")
        f.write("\n")
