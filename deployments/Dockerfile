FROM python:3.12-slim

# Set work directory
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface

# Install system dependencies
# - tesseract-ocr (+ Indonesian) is needed by pytesseract in the image loader
# - libgl1 / libglib2.0-0 are needed by docling's OpenCV dependency
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-ind \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies using uv for faster resolution.
# Install CPU-only torch first so the CUDA wheels (~3 GB) are not pulled in.
COPY requirements.txt .
RUN pip install --no-cache-dir uv \
    && uv pip install --system --no-cache torch --index-url https://download.pytorch.org/whl/cpu \
    && uv pip install --system --no-cache -r requirements.txt

# Bake models into the image so cold starts don't download them:
# router + semantic cache encoder, the document indexing embedder, and the FlashRank reranker
# (reranker.py loads it from ./.flashrank_cache, i.e. /app/.flashrank_cache).
RUN python -c "from sentence_transformers import SentenceTransformer as S; \
S('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); S('BAAI/bge-small-en-v1.5'); \
from flashrank import Ranker; Ranker(cache_dir='/app/.flashrank_cache')"

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8080

ENV CLOUD_RUN="1"
ENV PHOENIX_WORKING_DIR="/tmp/phoenix_data"

# Cloud Run injects PORT. --proxy-headers/--forwarded-allow-ips make the rate limiter
# see the real client IP from X-Forwarded-For instead of Google's front end.
CMD uvicorn src.interface.api:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 \
    --proxy-headers --forwarded-allow-ips="*" --timeout-keep-alive 75
