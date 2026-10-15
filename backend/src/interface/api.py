import os
# --- Arize Phoenix: SET ENV VAR FIRST before ANY imports ---
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV"):
    os.environ["PHOENIX_WORKING_DIR"] = "/tmp/phoenix_data"
else:
    os.environ["PHOENIX_WORKING_DIR"] = os.path.join(_PROJECT_ROOT, "src", "infrastructure", "phoenix_data")

os.makedirs(os.environ["PHOENIX_WORKING_DIR"], exist_ok=True)

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from fastapi import FastAPI
# --- Arize Phoenix: INITIALISE ---
from src.infrastructure.monitoring.phoenix_setup import setup_phoenix
setup_phoenix()

from fastapi.middleware.cors import CORSMiddleware

# --- Rate Limiting ---
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.interface.rate_limiter import limiter

# --- Routers ---
from src.interface.routes import auth, history, documents, monitoring, chat, data_analysis, report, settings

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Preload ML Models to prevent cold-start latency ---
    print("Preloading ML models...")
    try:
        from src.application.nlq.handle_chat import get_semantic_router_hf
        get_semantic_router_hf()
        
        from src.application.rag.reranker import rerank
        # Preload the FlashRank model with a dummy query
        from types import SimpleNamespace
        dummy_node = SimpleNamespace(node=SimpleNamespace(text="dummy"), score=1.0)
        rerank("dummy", [dummy_node])
        print("ML models loaded successfully.")
    except Exception as e:
        print(f"Failed to preload models: {e}")
    yield

app = FastAPI(title="RAG Pro API", version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
else:
    allowed_origins = ["*"]  # Fallback to all for demo/easy deployment

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- Include Routers ---
app.include_router(auth.router)
app.include_router(history.router)
app.include_router(documents.router)
app.include_router(monitoring.router)
app.include_router(chat.router)
app.include_router(data_analysis.router)
app.include_router(report.router)
app.include_router(settings.router)
