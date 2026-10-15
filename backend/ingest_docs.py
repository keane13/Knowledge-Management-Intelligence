"""
Proper Bulk Ingest menggunakan semantic chunking (SemanticSplitterNodeParser).
Menggunakan loader yang sudah ada (loader.py + index_document.py logic).

PENTING: Jalankan saat uvicorn SERVER DIMATIKAN untuk menghindari OOM.
Perintah:
    .\\labenv\\Scripts\\python.exe ingest_docs.py
"""
import os, sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("[INFO] Memulai Semantic Ingest Pipeline...")
    print("[INFO] Menggunakan SemanticSplitterNodeParser (BAAI/bge-small-en-v1.5)")
    print("[INFO] Pastikan uvicorn server sudah dimatikan untuk menghindari OOM!")
    print()

    from src.application.rag.vectorstore import (
        get_weaviate_client, setup_settings, get_vectorstore, init_knowledge_base
    )
    from src.application.rag.loader import load_documents
    from src.infrastructure.config.configs import DOCS_PATH
    from llama_index.core import VectorStoreIndex
    from llama_index.core.node_parser import SemanticSplitterNodeParser
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    # 1. Load docs dengan Docling (OCR dinonaktifkan untuk kecepatan)
    print(f"[LOAD] Memuat dokumen dari: {DOCS_PATH}")
    docs = load_documents(DOCS_PATH)

    if not docs:
        print("[WARN] Tidak ada dokumen yang berhasil dimuat!")
        return

    print(f"[LOAD] {len(docs)} dokumen berhasil dimuat\n")

    # 2. Semantic Chunking
    print("[CHUNK] Inisialisasi HuggingFace Embedding untuk semantic splitting...")
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    splitter = SemanticSplitterNodeParser(
        buffer_size=1,
        breakpoint_percentile_threshold=95,
        embed_model=embed_model
    )
    setup_settings()

    print("[CHUNK] Memulai Semantic Chunking (ini mungkin butuh beberapa menit)...")
    nodes = splitter.get_nodes_from_documents(docs)

    # Strip lokal embedding agar Weaviate yang vectorize dengan Snowflake Arctic
    for node in nodes:
        node.embedding = None

    print(f"[CHUNK] Total semantic chunks: {len(nodes)}\n")

    # 3. Clear data lama & re-index ke Weaviate
    client = get_weaviate_client()

    print("[CLEAR] Menghapus seluruh koleksi lama di Weaviate...")
    client.collections.delete_all()
    init_knowledge_base()

    vector_store = get_vectorstore()

    print(f"[INDEX] Mendorong {len(nodes)} chunks ke Weaviate Cloud...")
    VectorStoreIndex(nodes=nodes, vector_store=vector_store)

    # Verifikasi
    collection = client.collections.get("KnowledgeBase")
    final_count = collection.aggregate.over_all(total_count=True).total_count

    print()
    print("=" * 60)
    print("[DONE] SEMANTIC INGEST SELESAI!")
    print(f"   Dokumen diproses : {len(docs)}")
    print(f"   Semantic chunks  : {len(nodes)}")
    print(f"   Total di Weaviate: {final_count}")
    print()
    print("[INFO] Sekarang Anda bisa menjalankan uvicorn server kembali.")
    client.close()


if __name__ == "__main__":
    main()
