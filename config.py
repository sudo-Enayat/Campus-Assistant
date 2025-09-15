import os
from pathlib import Path

class Config:
    # Paths
    BASE_DIR = Path(__file__).parent
    DATA_DIR = BASE_DIR / "data"
    MODELS_DIR = BASE_DIR / "models" 
    CHROMA_DIR = BASE_DIR / "chroma_db"
    
    # Model settings
    DEFAULT_MODEL = "gemma-3-4b-it-Q4_K_M.gguf"  # Default model name
    MAX_TOKENS = 512
    TEMPERATURE = 0.3
    
    # RAG settings
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    TOP_K_RETRIEVAL = 3
    
    # Supported languages
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'hi': 'Hindi', 
        'bn': 'Bengali',
    }
    
    # Create directories if they don't exist
    DATA_DIR.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(exist_ok=True)
    CHROMA_DIR.mkdir(exist_ok=True)
