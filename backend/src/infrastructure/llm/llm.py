from groq import Groq
from src.infrastructure.config.configs import GROQ_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY
import base64
from pathlib import Path
from openai import OpenAI

groq_client = Groq(api_key=GROQ_API_KEY)

# Gemini client via OpenAI SDK
gemini_client = OpenAI(
    api_key=GEMINI_API_KEY or "dummy",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# Ollama client via OpenAI SDK
ollama_client = OpenAI(
    api_key="ollama", # required but ignored
    base_url="http://localhost:11434/v1"
)

from openrouter import OpenRouter

# ─────────────────────────────────────────────
# MODEL REGISTRY
# ─────────────────────────────────────────────

TEXT_MODELS = {
    "gemini-flash-lite": {
        "id": "gemini-2.5-flash", # User requested gemini-flash-lite-latest which maps to gemini-2.5-flash for standard tasks
        "label": "Gemini Flash Lite",
        "description": "Fast & efficient model via Google AI Studio.",
        "context_window": 1048576,
        "provider": "gemini",
        "best_for": "text_generation",
        "fallback_id": "gemini-flash-lite",
    },
    "gemini-flash-lite-latest": {
        "id": "gemini-2.5-flash", 
        "label": "Gemini Flash Lite",
        "description": "Fast & efficient model via Google AI Studio.",
        "context_window": 1048576,
        "provider": "gemini",
        "best_for": "text_generation",
        "fallback_id": "gemini-flash-lite-latest",
    },
    "ollama-local": {
        "id": "qwen2.5:3b",
        "label": "Ollama Local (Secure)",
        "description": "Locally running secure open-source model.",
        "context_window": 32000,
        "provider": "ollama",
        "best_for": "text_generation",
        "fallback_id": "ollama-local",
    },
    "ollama-reasoning": {
        "id": "qwen3:4b",
        "label": "Ollama Reasoning",
        "description": "Local reasoning model.",
        "context_window": 32000,
        "provider": "ollama",
        "best_for": "reasoning",
        "fallback_id": "ollama-reasoning",
    },
    "gemma-4-31b-it": {
        "id": "google/gemma-4-31b-it:free",
        "label": "google/gemma-4-31b-it",
        "description": "Fast & efficient. Great for RAG and summarisation.",
        "context_window": 131072,
        "provider": "openrouter",
        "best_for": "text_generation",
        "fallback_id": "google/gemma-4-31b-it:free",
    },
    "qwen3.6-27b": {
        "id": "qwen/qwen3.6-27b",
        "label": "qwen3.6-27b",
        "description": "More capable variant for complex Deep reasoning tasks.",
        "context_window": 131072,
        "provider": "groq",
        "best_for": "text_generation",
        "fallback_id": "qwen/qwen3.6-27b",
    },
    "gpt-oss-20b": {
        "id": "openai/gpt-oss-20b:free",
        "label": "gpt-oss-20b",
        "description": "More capable variant for fast & reliable conversation.",
        "context_window": 262144,
        "provider": "openrouter",
        "best_for": "text_generation",
        "fallback_id": "openai/gpt-oss-20b:free",
    },
    "gemma-4-26b-a4b": {
        "id": "google/gemma-4-26b-a4b-it:free",
        "label": "gemma-4-26b-a4b-it",
        "description": "High-quality 70B model, best accuracy for text tasks.",
        "context_window": 128000,
        "provider": "openrouter",
        "best_for": "text_generation",
        "fallback_id": "google/gemma-4-26b-a4b-it:free",
    },
    "nvidia/nemotron-nano-9b-v2": {
        "id": "nvidia/nemotron-nano-9b-v2:free",
        "label": "nemotron-nano-9b-v2",
        "description": "High-quality 70B model, best accuracy for text tasks.",
        "context_window": 128000,
        "provider": "openrouter",
        "best_for": "text_generation",
        "fallback_id": "nvidia/nemotron-nano-9b-v2:free",
    },
    "llama-3.3-70b-versatile": {
        "id": "llama-3.3-70b-versatile",
        "label": "llama-3.3-70b-versatile",
        "description": "Ultra-fast, low-latency model for simple queries.",
        "context_window": 128000,
        "provider": "groq",
        "best_for": "text_generation",
        "fallback_id": "llama-3.3-70b-versatile",
    },
    "qwen3-4b": {
        "id": "qwen/qwen3-4b:free",
        "label": "Qwen3 4B",
        "description": "Ultra-fast, low-latency model for simple queries.",
        "context_window": 40960,
        "provider": "openrouter",
        "best_for": "text_generation",
        "fallback_id": "meta-llama/llama-3.1-8b-instruct:free",
    },
   
}

VISION_MODELS = {
    "llama-3.2-11b-vision": {
        "id": "llama-3.2-11b-vision-preview",
        "label": "Llama Vision (Groq)",
        "description": "Fast and accurate vision model via Groq.",
        "context_window": 128000,
        "provider": "groq",
        "best_for": "vision",
        "recommended": True,
        "fallback_id": "llama-3.2-11b-vision-preview",
    },
    "nemotron-3-nano": {
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "label": "Nemo Nano Vision",
        "description": "Best balance of speed and vision capability. Recommended.",
        "context_window": 256000,
        "provider": "openrouter",
        "best_for": "vision",
        "recommended": False,
        "fallback_id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    },
    "gemma-vision-free": {
        "id": "google/gemma-4-26b-a4b-it:free",
        "label": "Gemma Vision (Free)",
        "description": "Google Gemma 26B Vision Model",
        "context_window": 128000,
        "provider": "openrouter",
        "best_for": "vision",
        "recommended": True,
        "fallback_id": "google/gemma-4-26b-a4b-it:free",
    },
}

# Default models
DEFAULT_TEXT_MODEL      = "gemma-4-31b-it"
DEFAULT_VISION_MODEL    = "gemma-vision-free"

# Reasoning fallback chain (tried in order on failure)
REASONING_FALLBACK_CHAIN = [
    "qwen3.6-27b",             # Primary: OpenRouter (Free)
    "gemma-4-31b-it",          # Fallback 1: OpenRouter (Free)
    "llama-3.3-70b-versatile", # Fallback 2: Groq, reliable
]

# Graph analytic model (lighter, fast)
GRAPH_ANALYTIC_MODEL = "llama-3.3-70b-versatile"


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

def _call_groq(model_id: str, messages, stream: bool, max_tokens: int = 2000):
    """Panggil Groq API dengan API key dinamis."""
    settings = load_settings()
    temp = settings.get("temperature", 0.3)
    key = settings.get("groq_api_key") or GROQ_API_KEY
    
    client = Groq(api_key=key) if key != GROQ_API_KEY else groq_client
    
    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temp,
        max_tokens=max_tokens,
        stream=stream,
    )
    return response if stream else response.choices[0].message.content

def _call_gemini(model_id: str, messages, stream: bool, max_tokens: int = 2000):
    """Panggil Gemini API via OpenAI SDK dengan API key dinamis."""
    settings = load_settings()
    temp = settings.get("temperature", 0.3)
    key = settings.get("gemini_api_key") or GEMINI_API_KEY
    
    client = OpenAI(
        api_key=key or "dummy",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
    
    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temp,
        max_tokens=max_tokens,
        stream=stream,
    )
    return response if stream else response.choices[0].message.content

def _call_ollama(model_id: str, messages, stream: bool, max_tokens: int = 2000):
    """Panggil Ollama lokal via OpenAI SDK dengan URL dinamis."""
    settings = load_settings()
    temp = settings.get("temperature", 0.3)
    url = settings.get("ollama_url", "http://localhost:11434/v1")
    
    client = OpenAI(
        api_key="ollama",
        base_url=url
    )
    
    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temp,
        max_tokens=max_tokens,
        stream=stream,
    )
    return response if stream else response.choices[0].message.content

def _call_openrouter(model_id: str, messages, stream: bool, max_tokens: int = 2000):
    """Panggil OpenRouter API menggunakan SDK openrouter."""
    with OpenRouter(api_key=OPENROUTER_API_KEY) as client:
        # Note: We use chat.completions.create if supported, otherwise chat.send
        # Since it is an OpenAI compatible API according to the docstring,
        # we can try chat.completions.create, but user provided client.chat.send
        response = client.chat.send(
            model=model_id,
            messages=messages,
            max_tokens=max_tokens,
        )
        # The user's SDK might not support native generator streaming via chat.send easily,
        # so we will just return the full text for now.
        if stream:
            # Fake streaming if actual streaming is not supported by this method
            def fake_stream():
                class Delta:
                    def __init__(self, content):
                        self.content = content
                class Choice:
                    def __init__(self, content):
                        self.delta = Delta(content)
                class Chunk:
                    def __init__(self, content):
                        self.choices = [Choice(content)]
                
                content = response.choices[0].message.content
                # stream character by character or word by word
                words = content.split(" ")
                for i, w in enumerate(words):
                    yield Chunk(w + (" " if i < len(words)-1 else ""))
            return fake_stream()
            
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
        if prov == "openrouter":
            return _call_openrouter(m_id, messages, stream)
        elif prov == "gemini":
            return _call_gemini(m_id, messages, stream)
        elif prov == "ollama":
            return _call_ollama(m_id, messages, stream)
        else:
            return _call_groq(m_id, messages, stream)

    try:
        return route_call(provider, model_id)
    except Exception as e:
        if _is_rate_limit_error(e):
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
            if provider == "openrouter":
                return _call_openrouter(model_id, messages, stream)
            elif provider == "gemini":
                return _call_gemini(model_id, messages, stream, max_tokens=max_tokens)
            elif provider == "ollama":
                return _call_ollama(model_id, messages, stream, max_tokens=max_tokens)
            else:
                return _call_groq(model_id, messages, stream, max_tokens=max_tokens)
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

    if provider == "openrouter":
        try:
            return _call_openrouter(model_id, messages, stream, max_tokens=1024)
        except Exception as e:
            if _is_rate_limit_error(e):
                fallback_id = _get_fallback_id(model_key, VISION_MODELS)
                print(f"⚠️ OpenRouter Vision limit. Fallback ke {fallback_id}...")
                return _call_openrouter(fallback_id, messages, stream, max_tokens=1024)
            raise e

    else:  # provider == "groq"
        try:
            return _call_groq(model_id, messages, stream, max_tokens=1024)
        except Exception as e:
            if _is_rate_limit_error(e):
                fallback_id = _get_fallback_id(model_key, VISION_MODELS)
                print(f"⚠️ Groq Vision limit. Fallback ke OpenRouter {fallback_id}...")
                return _call_openrouter(fallback_id, messages, stream, max_tokens=1024)
            raise e