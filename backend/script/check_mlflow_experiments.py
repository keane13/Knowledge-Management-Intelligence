import mlflow
import pandas as pd

mlflow.set_tracking_uri("file:./mlruns")
experiments = mlflow.search_experiments()
print("Experiments:")
for exp in experiments:
    print(f"Name: {exp.name}, ID: {exp.experiment_id}")

    df = mlflow.search_runs(experiment_ids=[exp.experiment_id])
    if 'metrics.bert_score_f1' in df.columns:
        target_runs = df[df['metrics.bert_score_f1'].notna()]
        print(f"  Found {len(target_runs)} runs with bert_score_f1 in {exp.name}.")
        avg_bert = target_runs['metrics.bert_score_f1'].mean()
        print(f"  Average BERT Score F1 in {exp.name}: {avg_bert}")
        
    if 'metrics.avg_bert_score' in df.columns:
        print("  Found 'metrics.avg_bert_score' in columns!")
        
    for col in df.columns:
        if 'bert' in col.lower() or 'score' in col.lower():
            print(f"  Metric col: {col}")
