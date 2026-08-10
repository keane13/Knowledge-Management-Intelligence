from collections import defaultdict
from .vectorstore import get_weaviate_client, get_embeddings
from .loader import load_documents
from .splitter_semantic import split_docs_semantic
from langchain_weaviate.vectorstores import WeaviateVectorStore
from src.infrastructure.config.configs import DOCS_PATH


def build_index():
    # 1️⃣ Load documents
    docs = load_documents(DOCS_PATH)

    if not docs:
        print("⚠️ No documents loaded")
        return

    # 2️⃣ Chunking (MANDATORY for RAG)
    chunks = split_docs_semantic(docs)

    print(f"📄 Documents: {len(docs)}")
    print(f"✂️ Chunks: {len(chunks)}")

    client = get_weaviate_client()
    embeddings = get_embeddings()

    import weaviate.classes.config as wvc
    
    collection_name = "KnowledgeBase"
    print(f"📦 Indexing {len(chunks)} chunks to collection: {collection_name}")
    
    # Menghapus semua koleksi lama karena Weaviate Sandbox membatasi maksimal 1 koleksi
    print("   🧹 Membersihkan koleksi lama di Weaviate Sandbox...")
    client.collections.delete_all()
    
    if not client.collections.exists(collection_name):
        print(f"   ⚙️ Creating collection {collection_name} (Using local BAAI/bge-small embeddings)...")
        client.collections.create(
            name=collection_name,
            vectorizer_config=wvc.Configure.Vectorizer.none()
        )
        
    vectorstore = WeaviateVectorStore(
        client=client,
        index_name=collection_name,
        text_key="text",
        embedding=embeddings,
    )
    vectorstore.add_documents(chunks)

    print("✅ Indexing selesai")


if __name__ == "__main__":
    build_index()
