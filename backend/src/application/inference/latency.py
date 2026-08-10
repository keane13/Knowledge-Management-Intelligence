import time
from contextlib import contextmanager

@contextmanager
def timer(name, metrics):
    start = time.perf_counter()
    yield
    metrics[name] = round(time.perf_counter() - start, 4)
