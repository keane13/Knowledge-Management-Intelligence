import os
from dotenv import load_dotenv

load_dotenv()
load_dotenv(".env.local")

def get_secret(secret_id: str, default: str = None) -> str:
    # 1. Fallback to local .env first (for local dev)
    val = os.getenv(secret_id)
    if val:
        return val
        
    # 2. Try Google Cloud Secret Manager if project ID is set
    project_id = os.getenv("GCP_PROJECT_ID")
    if project_id:
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            print(f"Warning: Failed to fetch {secret_id} from Secret Manager: {e}")
            
    return default

OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
WEAVIATE_URL = get_secret("WEAVIATE_URL")
WEAVIATE_API_KEY = get_secret("WEAVIATE_API_KEY")
GROQ_API_KEY = get_secret("GROQ_API_KEY")
OPENROUTER_API_KEY = get_secret("OPENROUTER_API_KEY")
GEMINI_API_KEY = get_secret("GEMINI_API_KEY")


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

if os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV"):
    DOCS_PATH = os.path.join("/tmp", "docs")
else:
    DOCS_PATH = os.path.join(BASE_DIR, "data", "knowledge", "documents")

# Local development fallback / Vercel tmp persistence – no PostgreSQL required
if os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV"):
    _SQLITE_PATH = os.path.join("/tmp", "chat_history.db")
else:
    _SQLITE_PATH = os.path.join(BASE_DIR, "chat_history.db")
DATABASE_URL = f"sqlite:///{_SQLITE_PATH}"
