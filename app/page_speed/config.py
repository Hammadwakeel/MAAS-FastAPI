import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ───────────────────────────────────────────────────────────────────────────
    # Google API Keys
    # ───────────────────────────────────────────────────────────────────────────
    pagespeed_api_key: str
    gemini_api_key: str

    # Qdrant (vector DB) connection (optional; if not set, QdrantClient will use defaults)
    qdrant_url: str 
    qdrant_api_key: str 
    # Optional timeout (seconds) to use when creating clients or making calls
    qdrant_timeout: int = 60

    # ───────────────────────────────────────────────────────────────────────────
    # Chat & RAG Configuration
    # ───────────────────────────────────────────────────────────────────────────
    groq_api_key: str
    vectorstore_base_path: str = "./vectorstores"

    # ───────────────────────────────────────────────────────────────────────────
    # MongoDB Configuration (Local)
    # ───────────────────────────────────────────────────────────────────────────
    mongo_user: str
    mongo_password: str
    mongo_host: str
    mongo_db: str = "MAAS"
    mongo_collection: str = "chat_histories"

    @property
    def mongo_uri(self) -> str:
        # pw = quote_plus(self.mongo_password)
        # return (
        #     f"mongodb+srv://{self.mongo_user}:{pw}@{self.mongo_host}/"
        #     f"{self.mongo_db}?retryWrites=true&w=majority&ssl=true"
        # )


    # ───────────────────────────────────────────────────────────────────────────
    # local MongoDB Connection
    # ───────────────────────────────────────────────────────────────────────────
     
        return f"mongodb://localhost:27017/{self.mongo_db}"
    

    # ───────────────────────────────────────────────────────────────────────────
    # FastAPI Server Configuration
    # ───────────────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = int(os.getenv("port", 8080))
    debug: bool = False

    # ───────────────────────────────────────────────────────────────────────────
    # App Metadata (unchanged)
    # ───────────────────────────────────────────────────────────────────────────
    app_name: str = "PageSpeed Insights Report Generator"
    app_version: str = "1.0.0"
    app_description: str = (
        "Professional API for generating PageSpeed Insights reports "
        "using Google's APIs and Gemini AI"
    )

    # ───────────────────────────────────────────────────────────────────────────
    # Tell Pydantic to load from .env and ignore extras
    # ───────────────────────────────────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

# Single shared Settings instance
settings = Settings()