import os
from typing import List, Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ensure .env is explicitly loaded into os.environ before Settings initialization
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Regional-Language Personal Tutor"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Database
    DATABASE_URL: str = "sqlite:///./app.db"
    
    # Auth / JWT
    JWT_SECRET_KEY: str = "dev_hackathon_secret_key_change_me_987654321"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Storage & Upload limits
    MAX_UPLOAD_SIZE_MB: int = 20
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    VECTOR_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vectorstore")
    
    # Gemini API Keys pool
    GEMINI_API_KEYS: List[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def __init__(self, **values):
        super().__init__(**values)
        keys = []
        
        # 1. Discover all GEMINI_API_KEY_* environment variables
        for env_key, env_val in os.environ.items():
            if (env_key.startswith("GEMINI_API_KEY_") or env_key == "GEMINI_API_KEY" or env_key == "GOOGLE_API_KEY") and env_val and env_val.strip():
                val = env_val.strip()
                if val not in keys:
                    keys.append(val)
        
        # 2. Direct field fallback check
        for i in range(1, 10):
            val = getattr(self, f"GEMINI_API_KEY_{i}", None)
            if val and val.strip() and val.strip() not in keys:
                keys.append(val.strip())
                
        self.GEMINI_API_KEYS = keys

settings = Settings()

# Ensure target directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_DIR, exist_ok=True)
