import os
# --- Arize Phoenix: SET ENV VAR FIRST before ANY imports ---
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV"):
    os.environ["PHOENIX_WORKING_DIR"] = "/tmp/phoenix_data"
else:
    os.environ["PHOENIX_WORKING_DIR"] = os.path.join(_PROJECT_ROOT, "src", "infrastructure", "phoenix_data")

os.makedirs(os.environ["PHOENIX_WORKING_DIR"], exist_ok=True)

from fastapi import FastAPI
# --- Arize Phoenix: INITIALISE ---
from src.infrastructure.monitoring.phoenix_setup import setup_phoenix
setup_phoenix()

from fastapi.middleware.cors import CORSMiddleware
from src.infrastructure.database import init_db

# --- Rate Limiting ---
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.interface.rate_limiter import limiter

# --- Routers ---
from src.interface.routes import auth, history, documents, monitoring, chat, data_analysis, report, settings

app = FastAPI(title="RAG Pro API", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database
init_db()

# --- Include Routers ---
app.include_router(auth.router)
app.include_router(history.router)
app.include_router(documents.router)
app.include_router(monitoring.router)
app.include_router(chat.router)
app.include_router(data_analysis.router)
app.include_router(report.router)
app.include_router(settings.router)
