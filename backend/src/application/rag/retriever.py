import weaviate.classes.query as wq
from llama_index.core.schema import NodeWithScore, Document
from src.application.rag.vectorstore import get_weaviate_client

def retrieve(vectorstore, query, k=5, selected_files=None):
    """
    Mengambil dokumen menggunakan pencarian native Weaviate (nearText) 
    agar memanfaatkan embedding Snowflake dari sisi Weaviate Cloud.
    """
    client = get_weaviate_client()
    collection = client.collections.get("KnowledgeBase")
    
    filters = None
    if selected_files and len(selected_files) > 0:
        filters = wq.Filter.by_property("source").equal(selected_files[0])
        
    response = collection.query.near_text(
        query=query,
        limit=k,
        filters=filters,
        return_metadata=wq.MetadataQuery(score=True, distance=True)
    )
    
    nodes_with_score = []
    for obj in response.objects:
        # Weaviate VectorStoreIndex default stores node content in 'text' property
        text_content = obj.properties.get("text", "")
        # Other properties are metadata
        metadata = {key: val for key, val in obj.properties.items() if key != "text"}
        
        node = Document(text=text_content, metadata=metadata)
        score = obj.metadata.score if obj.metadata.score is not None else 0.0
        nodes_with_score.append(NodeWithScore(node=node, score=score))
        
    return nodes_with_score
