import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()  


def get_llm():
    """
    Returns a ChatGroq LLM instance using the GROQ API key
    stored in the environment.
    """
    from langchain_groq import ChatGroq

    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0,
        max_tokens=1024,
        api_key=os.getenv("GROQ_API_KEY", "")  
    )
    return llm

# ──────────────────────────────────────────────────────────────────────────────
# 1. Text Splitter (512 tokens per chunk, 100 token overlap)
# ──────────────────────────────────────────────────────────────────────────────
text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=100)

# ──────────────────────────────────────────────────────────────────────────────
# 2. Embeddings Model (HuggingFace BGE) on CPU
# ──────────────────────────────────────────────────────────────────────────────


# HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")

# from huggingface_hub import login

# login(HF_TOKEN)

# model_name = "BAAI/bge-small-en-v1.5"
# model_kwargs = {"device": "cpu"}
# encode_kwargs = {"normalize_embeddings": True}
# embeddings = HuggingFaceEmbeddings(
#     model_name=model_name, model_kwargs=model_kwargs, encode_kwargs=encode_kwargs
# )
    
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
