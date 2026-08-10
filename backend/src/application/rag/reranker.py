_reranker = None

def rerank(query, docs):
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    pairs = [(query, d.page_content) for d in docs]
    scores = _reranker.predict(pairs)
    return sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
