import os
from collections import defaultdict
from src.application.rag.vectorstore import get_weaviate_client, setup_settings, get_vectorstore, init_knowledge_base
from src.application.rag.loader import load_documents
from src.infrastructure.config.configs import DOCS_PATH
from llama_index.core import Document as LlamaDocument
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


def build_index():
    # 1️⃣ Load documents using existing custom logic (Docling + OCR)
    docs = load_documents(DOCS_PATH)

    if not docs:
        print("⚠️ No documents loaded")
        return

    llama_docs = docs

    print(f"📄 Documents: {len(llama_docs)}")

    # 2️⃣ Setup Embeddings & Chunking (LlamaIndex)
    print("⚙️ Mengkonfigurasi LlamaIndex Settings...")
    setup_settings()
    
    # We use a Semantic Splitter Node Parser from LlamaIndex
    # Ini jauh lebih superior karena memahami konteks semantik kalimat
    print("✂️ Memulai Semantic Chunking...")
    # Explicitly pass the embed model to the parser
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    splitter = SemanticSplitterNodeParser(
        buffer_size=1, breakpoint_percentile_threshold=95, embed_model=embed_model
    )
    
    nodes = splitter.get_nodes_from_documents(llama_docs)
    
    # Strip local embeddings so Weaviate generates them using Snowflake
    for node in nodes:
        node.embedding = None
        
    print(f"✂️ Chunks: {len(nodes)}")

    # 3️⃣ Indexing
    client = get_weaviate_client()
    collection_name = "KnowledgeBase"
    print(f"📦 Indexing {len(nodes)} chunks to collection: {collection_name}")
    
    # Menghapus semua koleksi lama karena Weaviate Sandbox membatasi maksimal 1 koleksi
    print("   🧹 Membersihkan koleksi lama di Weaviate Sandbox...")
    client.collections.delete_all()
    
    init_knowledge_base()
    
    # Membangun ulang VectorStoreIndex (otomatis mensetup Weaviate collection di bawahnya)
    vector_store = get_vectorstore()
    
    print("   ⚙️ Mendorong data ke Weaviate Cloud via LlamaIndex...")
    index = VectorStoreIndex(nodes=nodes, vector_store=vector_store)

    print("✅ Indexing selesai")


if __name__ == "__main__":
    build_index()
