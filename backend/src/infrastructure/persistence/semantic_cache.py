import os
import re
import json
import logging
import datetime
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from src.infrastructure.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)
CACHE_COLLECTION = "semantic_cache"

# Cosine similarity needed for a hit. Measured with paraphrase-multilingual-MiniLM-L12-v2:
# Indonesian paraphrases score ~0.91-0.99, different questions up to ~0.89.
DEFAULT_THRESHOLD = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.92"))
# Entries older than this are ignored (and deleted by a Firestore TTL policy on `expire_at`).
TTL_DAYS = int(os.getenv("SEMANTIC_CACHE_TTL_DAYS", "7"))
# Nearest neighbours to inspect; the closest one may fail the key check while a later one passes.
CANDIDATES = 5

_NUMBER_RE = re.compile(r"\d+")
# Words that flip the meaning of an otherwise near-identical question
_POLARITY_WORDS = {
    "terbesar", "terkecil", "tertinggi", "terendah", "terbanyak", "tersedikit",
    "termahal", "termurah", "terbaru", "terlama", "naik", "turun", "max", "min",
    "highest", "lowest", "largest", "smallest", "most", "least", "top", "bottom",
    "latest", "oldest", "increase", "decrease",
}


def cache_key_terms(query: str) -> list[str]:
    """Exact-match terms: every number (law number, year, top-N, ...) plus polarity words.

    Embeddings barely distinguish "UU 23/2011" from "UU 24/2007" or "terbesar" from
    "terkecil", so a cache hit also requires these terms to be identical.
    """
    lower = query.lower()
    numbers = {n.lstrip("0") or "0" for n in _NUMBER_RE.findall(lower)}
    words = set(re.findall(r"[a-z]+", lower)) & _POLARITY_WORDS
    return sorted(numbers | words)


def _encoder_name(encoder) -> str:
    return getattr(encoder, "name", None) or type(encoder).__name__


def get_semantic_match(query: str, encoder, namespace: str = "rag", threshold: float | None = None):
    if len(query.strip()) < 5:
        return None
    threshold = DEFAULT_THRESHOLD if threshold is None else threshold
    try:
        db = get_firestore_client()
        # semantic-router encoders return a list of vectors
        query_vector = encoder([query])[0]
        key_terms = cache_key_terms(query)
        model = _encoder_name(encoder)
        now = datetime.datetime.now(datetime.timezone.utc)

        # Firestore COSINE distance is 1 - cosine_similarity.
        max_distance = 1.0 - threshold
        results = db.collection(CACHE_COLLECTION).find_nearest(
            vector_field="embedding",
            query_vector=Vector(query_vector),
            distance_measure=DistanceMeasure.COSINE,
            limit=CANDIDATES,
            distance_result_field="vector_distance"
        ).get()

        for doc in results:
            entry = doc.to_dict() or {}
            distance = entry.get("vector_distance")
            if distance is None or distance > max_distance:
                break  # results are sorted by distance
            expire_at = entry.get("expire_at")
            if (entry.get("namespace") != namespace
                    or entry.get("encoder_model") != model
                    or entry.get("key_terms") != key_terms
                    or (isinstance(expire_at, datetime.datetime) and expire_at < now)):
                continue
            data = entry.get("data")
            if data:
                logger.info(f"Cache HIT [{namespace}] (distance {distance:.4f}) for query: {query}")
                return json.loads(data)

        logger.info(f"Cache MISS [{namespace}] for query: {query}")
    except Exception as e:
        logger.error(f"Cache lookup error: {e}")
    return None


def set_semantic_cache(query: str, data: dict, encoder, namespace: str = "rag"):
    if len(query.strip()) < 10:
        return
    try:
        db = get_firestore_client()
        query_vector = encoder([query])[0]
        now = datetime.datetime.now(datetime.timezone.utc)

        doc_ref = db.collection(CACHE_COLLECTION).document()
        doc_ref.set({
            "query": query.strip().lower(),
            "namespace": namespace,
            "key_terms": cache_key_terms(query),
            "encoder_model": _encoder_name(encoder),
            "data": json.dumps(data),
            "embedding": Vector(query_vector),
            "created_at": now,
            "expire_at": now + datetime.timedelta(days=TTL_DAYS),
        })
        logger.info(f"Saved to semantic cache [{namespace}]: {query}")
    except Exception as e:
        logger.error(f"Cache write error: {e}")
