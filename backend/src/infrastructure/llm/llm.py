from src.infrastructure.config.configs import GROQ_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY
import base64
from pathlib import Path
import os
import litellm
from src.infrastructure.llm.timeouts import LLM_REQUEST_TIMEOUT_S

os.environ["GROQ_API_KEY"] = GROQ_API_KEY
os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY

# ─────────────────────────────────────────────
# MODEL REGISTRY
# ─────────────────────────────────────────────

TEXT_MODELS = {
    # ─── GEMINI MODELS ───
    "gemini-flash-lite-latest": {
        "id": "gemini-flash-lite-latest", 
        "label": "Gemini Flash Lite (Latest)",
        "description": "Ultra fast, best for Fast Mode & Query Rewriting.",
        "context_window": 1048576,
        "provider": "gemini",
        "best_for": "fast",
        "fallback_id": "groq-llama-fast",
    },
    "gemini-3-flash-preview": {
        "id": "gemini-3-flash-preview", 
        "label": "Gemini 3 Flash Preview",
        "description": "High reasoning capability, best for step-by-step thinking.",
        "context_window": 1048576,
        "provider": "gemini",
        "best_for": "reasoning",
        "fallback_id": "groq-qwen-reasoning",
    },
    "gemini-3.5-flash-lite": {
        "id": "gemini-3.5-flash-lite", 
        "label": "Gemini 3.5 Flash Lite",
        "description": "Deep analytic and heavy synthesis model.",
        "context_window": 2097152,
        "provider": "gemini",
        "best_for": "deep_analytic",
        "fallback_id": "groq-openai-oss",
    },
    
    # ─── GROQ MODELS ───
    "llama-3.3-70b-versatile": {
        "id": "llama-3.3-70b-versatile",
        "label": "Llama 3.3 70B (Groq)",
        "description": "High performance versatile model.",
        "context_window": 128000,
        "provider": "groq",
        "best_for": "reasoning",
        "fallback_id": "groq-openai-oss",
    },
    "groq-llama-fast": {
        "id": "groq/llama-3.1-8b-instant",
        "label": "Llama 8B (Groq)",
        "description": "Fallback for fast mode.",
        "context_window": 128000,
        "provider": "groq",
        "best_for": "fast",
        "fallback_id": "ollama-fast",
    },
    "groq-qwen-reasoning": {
        "id": "groq/qwen-2.5-32b",
        "label": "Qwen Reasoning (Groq)",
        "description": "Best for complex reasoning tasks.",
        "context_window": 128000,
        "provider": "groq",
        "best_for": "reasoning",
        "fallback_id": "gemini-3-flash-preview",
    },
    "groq-openai-oss": {
        "id": "groq/openai-oss",
        "label": "OpenAI OSS (Groq)",
        "description": "Powerful analytic fallback.",
        "context_window": 128000,
        "provider": "groq",
        "best_for": "deep_analytic",
        "fallback_id": "ollama-reasoning",
    },

    # ─── OLLAMA MODELS (LOCAL) ───
    "ollama-fast": {
        "id": "ollama/qwen2.5:3b",
        "label": "Ollama Fast (Local)",
        "description": "Local secure fast model.",
        "context_window": 32000,
        "provider": "ollama",
        "best_for": "fast",
        "fallback_id": "ollama-fast",
    },
    "ollama-reasoning": {
        "id": "ollama/qwen3:4b",
        "label": "Ollama Reasoning (Local)",
        "description": "Local secure reasoning model.",
        "context_window": 32000,
        "provider": "ollama",
        "best_for": "reasoning",
        "fallback_id": "ollama-reasoning",
    },
}

VISION_MODELS = {
    "gemini-3.1-flash-lite-multimodal": {
        "id": "gemini-3.1-flash-lite",
        "label": "Gemini 3.1 Flash Lite Multimodal",
        "description": "Primary vision and multimodal model.",
        "context_window": 1048576,
        "provider": "gemini",
        "best_for": "vision",
        "recommended": True,
        "fallback_id": "groq-llama-vision",
    },
    "groq-llama-vision": {
        "id": "groq/llama-3.2-11b-vision-preview",
        "label": "Llama Vision (Groq)",
        "description": "Fallback vision model.",
        "context_window": 128000,
        "provider": "groq",
        "best_for": "vision",
        "recommended": False,
        "fallback_id": "groq-llama-vision",
    }
}

# Default models
DEFAULT_TEXT_MODEL      = "gemini-flash-lite-latest"
DEFAULT_VISION_MODEL    = "gemini-3.1-flash-lite-multimodal"

# Fallback Chains (tried in order on failure)
FAST_FALLBACK_CHAIN = [
    "gemini-flash-lite-latest",
    "groq-llama-fast",
    "ollama-fast"
]

REASONING_FALLBACK_CHAIN = [
    "groq-qwen-reasoning",
    "gemini-3-flash-preview",
    "ollama-reasoning"
]

DEEP_ANALYTIC_CHAIN = [
    "gemini-3.5-flash-lite",
    "groq-openai-oss",
    "ollama-reasoning"
]

GRAPH_ANALYTIC_MODEL = "gemini-3.5-flash-lite"


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _get_fallback_id(model_key: str, registry: dict) -> str:
    """Mendapatkan ID model cadangan dari registry."""
    if model_key in registry and "fallback_id" in registry[model_key]:
        return registry[model_key]["fallback_id"]
    return "gemini-flash-lite-latest"


def _image_to_data_url(image_path: str) -> str:
    """Encode a local image as a base64 data URL for the API."""
    path = Path(image_path)
    suffix = path.suffix.lower().lstrip(".")
    mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "bmp": "bmp"}
    mime = mime_map.get(suffix, "jpeg")
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/{mime};base64,{b64}"


# ─────────────────────────────────────────────
# INTERNAL CALL HELPERS
# ─────────────────────────────────────────────

from src.infrastructure.config.settings import load_settings

def _call_litellm(provider: str, model_id: str, messages, stream: bool, max_tokens: int = 2000):
    settings = load_settings()
    temp = settings.get("temperature", 0.3)
    
    if provider == "groq":
        litellm_model = f"groq/{model_id}"
    elif provider == "openrouter":
        litellm_model = f"openrouter/{model_id}"
    elif provider == "gemini":
        litellm_model = f"gemini/{model_id}"
    elif provider == "ollama":
        url = settings.get("ollama_url", "http://localhost:11434")
        litellm_model = f"ollama/{model_id}"
        os.environ["OLLAMA_API_BASE"] = url
    else:
        litellm_model = model_id
        
    response = litellm.completion(
        model=litellm_model,
        messages=messages,
        temperature=temp,
        max_tokens=max_tokens,
        stream=stream,
        # Seconds per HTTP request; for streams it also bounds the gap between chunks.
        timeout=LLM_REQUEST_TIMEOUT_S,
    )
    if stream:
        return response
    else:
        return response.choices[0].message.content


def _is_rate_limit_error(e: Exception) -> bool:
    """Cek apakah error disebabkan rate limit atau overload."""
    msg = str(e).lower()
    cls_name = e.__class__.__name__.lower()
    return any(k in msg for k in ["429", "402", "rate_limit", "overloaded", "too many requests", "credits", "provider returned error"]) or "toomanyrequests" in cls_name


# ─────────────────────────────────────────────
# TEXT GENERATION
# ─────────────────────────────────────────────

def generate_answer(messages, stream=False, model_key: str | None = None):
    if os.environ.get("MOCK_LLM") == "true":
        import time
        mock_text = "Ini adalah respons MOCK_LLM untuk keperluan load testing server secara gratis dan aman."
        if stream:
            def mock_stream():
                class Delta:
                    def __init__(self, content):
                        self.content = content
                class Choice:
                    def __init__(self, content):
                        self.delta = Delta(content)
                class Chunk:
                    def __init__(self, content):
                        self.choices = [Choice(content)]
                words = mock_text.split(" ")
                for i, w in enumerate(words):
                    yield Chunk(w + (" " if i < len(words)-1 else ""))
                    time.sleep(0.01)
            return mock_stream()
        return mock_text

    model_key   = model_key or "gemini-flash-lite-latest"
    model_info  = TEXT_MODELS.get(model_key, {})
    provider    = model_info.get("provider", "gemini")
    model_id    = model_info.get("id", model_key)

    def route_call(prov, m_id):
        return _call_litellm(prov, m_id, messages, stream)

    try:
        return route_call(provider, model_id)
    except Exception as e:
        if _is_rate_limit_error(e) or isinstance(e, litellm.Timeout):
            fallback_key = _get_fallback_id(model_key, TEXT_MODELS)
            
            # Extract info for fallback model
            fb_info = TEXT_MODELS.get(fallback_key, {})
            fb_prov = fb_info.get("provider", "groq") 
            fb_id = fb_info.get("id", fallback_key)
            
            print(f"⚠️ {provider} limit pada {model_id}. Fallback ke {fb_id} ({fb_prov})...")
            return route_call(fb_prov, fb_id)
        raise e


# ─────────────────────────────────────────────
# REASONING GENERATION (with fallback chain)
# ─────────────────────────────────────────────

def generate_reasoning_answer(
    messages,
    stream: bool = False,
    fallback_chain: list | None = None,
    max_tokens: int = 4000,
):
    """
    Memanggil model reasoning dengan fallback chain otomatis.
    Mencoba setiap model dalam chain sampai berhasil.
    """
    if os.environ.get("MOCK_LLM") == "true":
        import time
        mock_text = "[MOCK] Sub-task 1\\n[MOCK] Sub-task 2\\n" if not stream else "Ini adalah respons reasoning MOCK_LLM untuk load testing."
        if stream:
            def mock_stream():
                class Delta:
                    def __init__(self, content):
                        self.content = content
                class Choice:
                    def __init__(self, content):
                        self.delta = Delta(content)
                class Chunk:
                    def __init__(self, content):
                        self.choices = [Choice(content)]
                words = mock_text.split(" ")
                for i, w in enumerate(words):
                    yield Chunk(w + (" " if i < len(words)-1 else ""))
                    time.sleep(0.01)
            return mock_stream()
        return mock_text

    chain = fallback_chain or REASONING_FALLBACK_CHAIN

    last_exc = None
    for model_key in chain:
        model_info = TEXT_MODELS.get(model_key, {})
        provider   = model_info.get("provider", "openrouter")
        model_id   = model_info.get("id", model_key)
        try:
            print(f"🧠 Reasoning: mencoba model [{model_key}] provider [{provider}]")
            return _call_litellm(provider, model_id, messages, stream, max_tokens=max_tokens)
        except Exception as e:
            last_exc = e
            if _is_rate_limit_error(e):
                print(f"⚠️ Rate limit / error pada [{model_key}]: {e}. Mencoba model berikutnya...")
                continue
            # Non-rate-limit error — juga coba model berikutnya agar robust
            print(f"⚠️ Error pada [{model_key}]: {e}. Mencoba model berikutnya...")
            continue

    # Semua model gagal
    raise RuntimeError(
        f"Semua model reasoning gagal. Error terakhir: {last_exc}"
    )


# ─────────────────────────────────────────────
# VISION GENERATION
# ─────────────────────────────────────────────

def generate_vision_answer(
    prompt: str,
    image_input: str,
    stream: bool = False,
    model_key: str | None = None,
    system_prompt: str | None = None,
) -> str:
    model_key  = model_key or DEFAULT_VISION_MODEL
    model_info = VISION_MODELS.get(model_key, {})
    provider   = model_info.get("provider", "openrouter")
    model_id   = model_info.get("id", model_key)

    # Persiapan konten gambar
    if image_input.startswith("http") or image_input.startswith("data:image"):
        image_content = {"type": "image_url", "image_url": {"url": image_input}}
    else:
        data_url      = _image_to_data_url(image_input)
        image_content = {"type": "image_url", "image_url": {"url": data_url}}

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({
        "role": "user",
        "content": [image_content, {"type": "text", "text": prompt}],
    })

    try:
        return _call_litellm(provider, model_id, messages, stream, max_tokens=1024)
    except Exception as e:
        if _is_rate_limit_error(e):
            fallback_id = _get_fallback_id(model_key, VISION_MODELS)
            fb_provider = VISION_MODELS.get(fallback_id, {}).get("provider", "openrouter")
            print(f"⚠️ {provider} Vision limit. Fallback ke {fallback_id}...")
            return _call_litellm(fb_provider, fallback_id, messages, stream, max_tokens=1024)
        raise e