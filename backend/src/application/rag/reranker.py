_reranker = None

def rerank(query, nodes_with_score):
    """
    Melakukan reranking menggunakan FlashRank (ONNX) yang super ringan dan cepat.
    Telah diadaptasi untuk menerima list LlamaIndex NodeWithScore.
    """
    global _reranker
    if _reranker is None:
        from flashrank import Ranker
        _reranker = Ranker(cache_dir="./.flashrank_cache")
        
    if not nodes_with_score:
        return []

    from flashrank import RerankRequest

    # Siapkan format passages untuk FlashRank
    passages = []
    for i, n in enumerate(nodes_with_score):
        passages.append({"id": i, "text": n.node.text})

    rerank_req = RerankRequest(query=query, passages=passages)
    results = _reranker.rerank(rerank_req)
    
    # FlashRank mengembalikan dictionary dengan 'score' dan 'id'
    node_map = {i: n for i, n in enumerate(nodes_with_score)}
    
    reranked_nodes = []
    for res in results:
        node_idx = res["id"]
        original_node = node_map[node_idx]
        original_node.score = float(res["score"])
        reranked_nodes.append(original_node)
        
    return reranked_nodes
