import os
import json
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent.parent.parent.parent / "data" / "settings.json"

DEFAULT_SETTINGS = {
    "gemini_api_key": "",
    "groq_api_key": "",
    "ollama_url": "http://localhost:11434/v1",
    "temperature": 0.3
}

def load_settings() -> dict:
    """Load settings from JSON file. Returns default if not exists."""
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()
    
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            # Merge with defaults to ensure all keys exist
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            return merged
    except Exception as e:
        print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict) -> bool:
    """Save settings to JSON file."""
    try:
        # Ensure directory exists
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing first to merge
        current = load_settings()
        current.update(settings)
        
        with open(SETTINGS_FILE, "w") as f:
            json.dump(current, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False
