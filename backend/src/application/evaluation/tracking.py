import mlflow
import random

mlflow.set_experiment("rag-low-latency")

def log_metrics(metrics):
    if random.random() < 0.2:  # 🔥 sampling
        with mlflow.start_run():
            for k, v in metrics.items():
                mlflow.log_metric(k, v)
