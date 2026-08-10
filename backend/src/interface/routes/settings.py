from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.infrastructure.auth import get_current_user
from src.infrastructure.config.settings import load_settings, save_settings

router = APIRouter(tags=["Settings"])

class SettingsUpdate(BaseModel):
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    ollama_url: str | None = None
    temperature: float | None = None

def _mask_key(key: str) -> str:
    if not key or len(key) < 8:
        return ""
    return key[:4] + "..." + key[-4:]

@router.get("/settings")
def get_settings(current_user: str = Depends(get_current_user)):
    """Get current settings. API Keys are masked for security."""
    settings = load_settings()
    
    return {
        "gemini_api_key": _mask_key(settings.get("gemini_api_key", "")),
        "groq_api_key": _mask_key(settings.get("groq_api_key", "")),
        "ollama_url": settings.get("ollama_url", "http://localhost:11434/v1"),
        "temperature": settings.get("temperature", 0.3)
    }

@router.post("/settings")
def update_settings(data: SettingsUpdate, current_user: str = Depends(get_current_user)):
    """Update settings. Empty API keys will be ignored (not overwritten)."""
    current = load_settings()
    
    update_data = {}
    if data.gemini_api_key:
        update_data["gemini_api_key"] = data.gemini_api_key
    if data.groq_api_key:
        update_data["groq_api_key"] = data.groq_api_key
    if data.ollama_url is not None:
        update_data["ollama_url"] = data.ollama_url
    if data.temperature is not None:
        update_data["temperature"] = data.temperature
        
    if update_data:
        save_settings(update_data)
        
    return {"status": "success", "message": "Settings updated"}
