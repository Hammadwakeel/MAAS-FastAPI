from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus

class Settings(BaseSettings):
    # Google API Keys
    pagespeed_api_key: str
    gemini_api_key: str

    # Chat & RAG Configuration
    groq_api_key: str
    vectorstore_base_path: str = "./vectorstores"

    # Hugging Face
    huggingfacehub_api_token: str

    # MongoDB Config
    mongo_password: str
    mongo_chat_db: str = "MAAS"
    mongo_chat_collection: str = "chat_histories"

    # FastAPI Server Config
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # MongoDB Atlas URI (Dynamically Constructed)
    @property
    def mongo_uri(self):
        encoded_pwd = quote_plus(self.mongo_password)
        return f"mongodb+srv://Hammad:{encoded_pwd}@cluster0.oi9z5ig.mongodb.net/{self.mongo_chat_db}?retryWrites=true&w=majority"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Global settings instance
settings = Settings()
