import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import Any, Optional
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def get_llm(model: str = "gemini-2.5-flash",
            temperature: float = 0.0,
            max_tokens: Optional[int] = None,
            timeout: Optional[int] = None,
            max_retries: int = 3) -> Any:
    """
    Return a LangChain ChatGoogleGenerativeAI LLM configured to use Gemini.

    - Reads GEMINI_API_KEY from environment.
    - Default model: 'gemini-2.5-flash' (change if you need another).
    - Temperature default 0 for deterministic responses.
    - max_tokens/timeout can be None to allow defaults from the underlying client.

    Returns:
        An instance of langchain.chat_models.ChatGoogleGenerativeAI (or raises informative error).
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception as e:
        logger.exception("langchain ChatGoogleGenerativeAI import failed")
        raise RuntimeError(
            "langchain (with ChatGoogleGenerativeAI) is required but not installed. "
            "Install with: pip install 'langchain[google]' or refer to your LangChain version docs."
        ) from e

    # Prefer explicit environment variable or other configured setting
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        msg = "GEMINI_API_KEY environment variable not set. Set it to your Gemini API key."
        logger.error(msg)
        raise RuntimeError(msg)

    # Build client config
    try:
        llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            api_key=api_key,
        )
        logger.info("Initialized ChatGoogleGenerativeAI LLM (model=%s)", model)
        return llm
    except TypeError:
        # Some langchain versions may accept different parameter names (api_key vs openai_api_key etc.)
        # Try a safer fallback with only the most common args.
        try:
            llm = ChatGoogleGenerativeAI(model=model, temperature=temperature, api_key=api_key)
            logger.info("Initialized ChatGoogleGenerativeAI LLM (fallback constructor) model=%s", model)
            return llm
        except Exception as e:
            logger.exception("Failed to create ChatGoogleGenerativeAI instance")
            raise RuntimeError(f"Failed to initialize Gemini LLM: {e}") from e
    except Exception as e:
        logger.exception("Failed to initialize Gemini LLM")
        raise RuntimeError(f"Failed to initialize Gemini LLM: {e}") from e


# ──────────────────────────────────────────────────────────────────────────────
# 1. Text Splitter (512 tokens per chunk, 100 token overlap)
# ──────────────────────────────────────────────────────────────────────────────
text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=100)

# ──────────────────────────────────────────────────────────────────────────────
# 2. Embeddings Model
# ──────────────────────────────────────────────────────────────────────────────

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# 2. Embeddings Model (Google Gemini)
# ──────────────────────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is not set in environment variables")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=GOOGLE_API_KEY
)
