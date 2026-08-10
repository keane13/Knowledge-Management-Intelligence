import weaviate
from weaviate.classes.init import Auth
from langchain_weaviate.vectorstores import WeaviateVectorStore
from src.infrastructure.config.configs import WEAVIATE_API_KEY, WEAVIATE_URL
# ========= SINGLETONS =========

_client = None
_embeddings = None
_vectorstore = None


def get_weaviate_client():
    global _client
    if _client is None:
        _client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
            skip_init_checks=True
        )
    return _client


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        import os
        hf_token = os.environ.get("HUGGINGFACE_TOKEN")
        try:
            from langchain_huggingface import HuggingFaceEndpointEmbeddings
            _embeddings = HuggingFaceEndpointEmbeddings(
                model="BAAI/bge-small-en-v1.5",
                huggingfacehub_api_token=hf_token
            )
        except ImportError:
            # Fallback if EndpointEmbeddings isn't available
            from langchain_community.embeddings import HuggingFaceInferenceAPIEmbeddings
            _embeddings = HuggingFaceInferenceAPIEmbeddings(
                api_key=hf_token, model_name="BAAI/bge-small-en-v1.5"
            )
    return _embeddings


def get_vectorstore():
    """
    ⚡ FAST INFERENCE VECTORSTORE
    """
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = WeaviateVectorStore(
            client=get_weaviate_client(),
            embedding=get_embeddings(),
            index_name="KnowledgeBase",  # MUST MATCH schema
            text_key="text"
        )
    return _vectorstore