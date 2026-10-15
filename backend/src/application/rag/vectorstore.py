import weaviate
from weaviate.classes.init import Auth
from llama_index.vector_stores.weaviate import WeaviateVectorStore
from llama_index.core import VectorStoreIndex, Settings
from src.infrastructure.config.configs import WEAVIATE_API_KEY, WEAVIATE_URL

# ========= SINGLETONS =========

_client = None
_vectorstore = None
_index = None
_settings_configured = False


def get_weaviate_client():
    global _client
    if _client is None:
        _client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
            skip_init_checks=True
        )
    return _client


def init_knowledge_base():
    """Ensure KnowledgeBase collection exists with Snowflake Arctic vectorizer."""
    client = get_weaviate_client()
    if not client.collections.exists("KnowledgeBase"):
        import weaviate.classes.config as wc
        client.collections.create(
            "KnowledgeBase",
            vectorizer_config=wc.Configure.Vectorizer.text2vec_weaviate(
                model="Snowflake/snowflake-arctic-embed-l-v2.0"
            )
        )

def setup_settings():
    global _settings_configured
    if not _settings_configured:
        # Menjalankan BAAI/bge-small-en-v1.5 secara LOKAL untuk menghindari bottleneck API HF Gratis.
        # Jauh lebih stabil dan latensi konsisten dibandingkan API Endpoint.
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        
        Settings.embed_model = embed_model
        Settings.llm = None  # Kita menggunakan custom LLM router
        _settings_configured = True


def get_vectorstore():
    """
    ⚡ FAST INFERENCE VECTORSTORE (LlamaIndex Weaviate)
    """
    global _vectorstore
    if _vectorstore is None:
        init_knowledge_base()
        _vectorstore = WeaviateVectorStore(
            weaviate_client=get_weaviate_client(),
            index_name="KnowledgeBase",
        )
    return _vectorstore


def get_index():
    """
    Mendapatkan LlamaIndex VectorStoreIndex singleton.
    """
    global _index
    if _index is None:
        setup_settings()
        _index = VectorStoreIndex.from_vector_store(vector_store=get_vectorstore())
    return _index