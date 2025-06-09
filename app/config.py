import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env
load_dotenv()

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ───────────────────────────────────────────────────────────────────────────
    # Google API Keys
    # ───────────────────────────────────────────────────────────────────────────
    pagespeed_api_key: str = os.getenv("PAGESPEED_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # ───────────────────────────────────────────────────────────────────────────
    # Chat & RAG Configuration
    # ───────────────────────────────────────────────────────────────────────────
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    vectorstore_base_path: str = os.getenv("VECTORSTORE_BASE_PATH", "./vectorstores")

    # ───────────────────────────────────────────────────────────────────────────
    # MongoDB Configuration (Local)
    # ───────────────────────────────────────────────────────────────────────────
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_chat_db: str = os.getenv("MONGO_CHAT_DB", "Education_chatbot")
    mongo_chat_collection: str = os.getenv("MONGO_CHAT_COLLECTION", "chat_histories")

    # ───────────────────────────────────────────────────────────────────────────
    # FastAPI Server Configuration
    # ───────────────────────────────────────────────────────────────────────────
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

    # ───────────────────────────────────────────────────────────────────────────
    # App Metadata (unchanged)
    # ───────────────────────────────────────────────────────────────────────────
    app_name: str = "PageSpeed Insights Report Generator"
    app_version: str = "1.0.0"
    app_description: str = (
        "Professional API for generating PageSpeed Insights reports "
        "using Google's APIs and Gemini AI"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

# Instantiate settings
settings = Settings()
