import re
from langchain_core.documents import Document as LangchainDocument
from llama_index.core import Document as LlamaDocument
from llama_index.core.node_parser import SemanticSplitterNodeParser
from src.infrastructure.config.configs import OPENAI_API_KEY

def sanitize_metadata_keys(metadata: dict) -> dict:
    """Membersihkan metadata di tahap akhir agar Weaviate tidak error."""
    sanitized = {}
    for key, value in metadata.items():
        clean_key = re.sub(r'[^_A-Za-z0-9]', '_', key)
        if re.match(r'^[0-9]', clean_key):
            clean_key = f"_{clean_key}"
        clean_key = clean_key.lower()
        sanitized[clean_key] = value
    return sanitized

def split_docs_semantic(docs: list[LangchainDocument]):
    """
    Split documents using LlamaIndex Semantic Chunking.
    """
    if not docs:
        return []

    print("✂️ Initialize LlamaIndex Semantic Splitter...")
    # Initialize LlamaIndex Embedding with BAAI/bge-small-en-v1.5 (Fast, light, and better than MiniLM)
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")

    # Initialize SemanticSplitterNodeParser
    splitter = SemanticSplitterNodeParser(
        buffer_size=1, breakpoint_percentile=95, embed_model=embed_model
    )

    final_chunks = []
    
    for idx, doc in enumerate(docs):
        print(f"✂️ Semantic Splitting document {idx+1}/{len(docs)}: {doc.metadata.get('source', 'unknown')} (collection: {doc.metadata.get('collection', 'General')})")
        try:
            # 1. Convert Langchain Document -> LlamaIndex Document
            llama_doc = LlamaDocument(
                text=doc.page_content,
                metadata=doc.metadata
            )
            
            # 2. Get Nodes (Chunks)
            nodes = splitter.get_nodes_from_documents([llama_doc])
            
            # 3. Convert Nodes back to Langchain Document
            for node in nodes:
                # Merge metadata
                merged_metadata = doc.metadata.copy()
                if node.metadata:
                    merged_metadata.update(node.metadata)
                
                # Sanitize for Weaviate
                clean_metadata = sanitize_metadata_keys(merged_metadata)
                
                lc_chunk = LangchainDocument(
                    page_content=node.get_content(),
                    metadata=clean_metadata
                )
                final_chunks.append(lc_chunk)
                
        except Exception as e:
            print(f"❌ Error during semantic splitting: {e}")
            # Fallback for this document
            clean_metadata = sanitize_metadata_keys(doc.metadata)
            doc.metadata = clean_metadata
            final_chunks.append(doc)

    return final_chunks
