"""
Arize Phoenix setup – Cloud mode.

Phoenix will send traces to Arize Phoenix Cloud using the provided API key and Endpoint.
"""

import os
from dotenv import load_dotenv

# Load env vars to get API Key and Endpoint
load_dotenv()
load_dotenv(".env.local")

# ── Configure Phoenix for Cloud (Requires PHOENIX_API_KEY in .env) ──
PHOENIX_API_KEY = os.getenv("PHOENIX_API_KEY")
PHOENIX_COLLECTOR_ENDPOINT = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
if PHOENIX_API_KEY:
    os.environ["PHOENIX_CLIENT_HEADERS"] = f"api_key={PHOENIX_API_KEY}"
if PHOENIX_COLLECTOR_ENDPOINT:
    # Ensure it ends with /v1/traces for the OTel exporter
    if not PHOENIX_COLLECTOR_ENDPOINT.endswith("/v1/traces"):
        os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = f"{PHOENIX_COLLECTOR_ENDPOINT.rstrip('/')}/v1/traces"
    else:
        os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = PHOENIX_COLLECTOR_ENDPOINT
import phoenix as px
from opentelemetry import trace
from phoenix.otel import register as phoenix_register
from openinference.instrumentation.groq import GroqInstrumentor
from openinference.instrumentation.langchain import LangChainInstrumentor

_phoenix_initialized = False


def setup_phoenix() -> None:
    """
    Configure and wire up OpenTelemetry tracing to Phoenix Cloud.
    """
    global _phoenix_initialized
    if _phoenix_initialized:
        return

    if not PHOENIX_API_KEY:
        print("[WARNING] PHOENIX_API_KEY not found. Traces may not be sent to Cloud.")

    # 2. Register Phoenix as the global OTel TracerProvider
    tracer_provider = phoenix_register(project_name="rag_pro")

    # 4 & 5. Auto-instrument Groq SDK + LangChain
    GroqInstrumentor().instrument(tracer_provider=tracer_provider)
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    
    # 6. Instrument LiteLLM (for valid costs & token usage in Phoenix)
    try:
        from openinference.instrumentation.litellm import LiteLLMInstrumentor
        LiteLLMInstrumentor().instrument(tracer_provider=tracer_provider)
    except ImportError:
        print("[WARNING] LiteLLMInstrumentor not found.")

    # 7. Instrument HTTP Clients (for MCP toolbox latency tracing)
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        RequestsInstrumentor().instrument()
        HTTPXClientInstrumentor().instrument()
    except ImportError:
        print("[WARNING] HTTP instrumentors not found.")

    _phoenix_initialized = True
    print(f"[OK] Phoenix tracing ready - targeting Cloud endpoint {PHOENIX_COLLECTOR_ENDPOINT}")


def get_tracer(name: str = "rag_pro"):
    """Return a named OpenTelemetry tracer backed by Phoenix."""
    return trace.get_tracer(name)
