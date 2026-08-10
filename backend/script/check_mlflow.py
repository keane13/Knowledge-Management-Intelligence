import mlflow
import pandas as pd

mlflow.set_tracking_uri("file:./mlruns")
experiment = mlflow.get_experiment_by_name("RAG_System_Evaluation")
if experiment:
    df = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    with open("mlflow_output.txt", "w") as f:
        f.write("Columns: " + str(list(df.columns)) + "\n")
        f.write("Num runs: " + str(len(df)) + "\n")
        metric_cols = [c for c in df.columns if c.startswith('metrics.')]
        f.write("Metric columns: " + str(metric_cols) + "\n")
        if not df.empty and metric_cols:
            f.write(str(df[metric_cols].head(3)))
else:
    with open("mlflow_output.txt", "w") as f:
        f.write("Experiment not found\n")
