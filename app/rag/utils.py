import os
from typing import Optional, Dict, Any
from fastapi import HTTPException

from langchain_community.vectorstores import FAISS
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain.memory import ConversationBufferMemory                # ← IMPORT THIS
from langchain.chains import ConversationalRetrievalChain

from app.page_speed.config import settings
from .db import vectorstore_meta_coll, chat_collection_name
from .embeddings import embeddings, text_splitter, get_llm
from .logging_config import logger
from app.rag.prompt_library import page_speed_prompt, default_user_prompt,seo_prompt

# ──────────────────────────────────────────────────────────────────────────────
# 1. Helper: Path to Store (or Load) a User's FAISS Vectorstore on Disk
# ──────────────────────────────────────────────────────────────────────────────
def get_vectorstore_path(onboarding_id: str) -> str:
    """
    Ensure a local directory exists for this user's vectorstore.
    Returns a path like './vectorstores/{onboarding_id}'.
    """
    base_dir = settings.vectorstore_base_path
    user_dir = os.path.join(base_dir, onboarding_id)
    # os.makedirs(user_dir, exist_ok=True)
    return user_dir

# ──────────────────────────────────────────────────────────────────────────────
# 2. Build or Load an Existing FAISS Index for a User
# ──────────────────────────────────────────────────────────────────────────────
def build_or_load_vectorstore(onboarding_id: str) -> FAISS:
    """
    Attempt to load an existing FAISS index for this user.
    If not found on disk, raise a FileNotFoundError.
    """
    user_dir = get_vectorstore_path(onboarding_id)
    faiss_index_path = os.path.join(user_dir, "faiss_index")

    if not os.path.isdir(faiss_index_path):
        raise FileNotFoundError(f"No vectorstore found at {faiss_index_path}")

    # Allow loading your own index via pickle
    return FAISS.load_local(
        folder_path=faiss_index_path,
        embeddings=embeddings,
        allow_dangerous_deserialization=True
    )

# ──────────────────────────────────────────────────────────────────────────────
# 3. Save a FAISS Vectorstore to Disk for a User
# ──────────────────────────────────────────────────────────────────────────────
def save_vectorstore_to_disk(vectorstore: FAISS, vectorstore_name: str) -> str:
    """
    Save the FAISS vectorstore under './vectorstores/{user_id}/faiss_index'.
    Returns the path to that saved folder.
    """
    user_dir = get_vectorstore_path(vectorstore_name)
    faiss_index_path = os.path.join(user_dir, "faiss_index")
    os.makedirs(faiss_index_path, exist_ok=True)
    vectorstore.save_local(folder_path=faiss_index_path)
    return faiss_index_path

# ──────────────────────────────────────────────────────────────────────────────
# 4. Upsert or Fetch Vectorstore Metadata in MongoDB
# ──────────────────────────────────────────────────────────────────────────────
def upsert_vectorstore_metadata(onboarding_id: str, vectorstore_path: str, chat_id: str) -> None:
    """
    Insert or update a document mapping user_id → vectorstore_path in MongoDB.
    """
    vectorstore_meta_coll.update_one(
        {"onboarding_id": onboarding_id},
        {"$set": {"vectorstore_path": vectorstore_path}, 
         "$setOnInsert": {"chat_id": chat_id}},
        upsert=True
    )

def get_vectorstore_metadata(onboarding_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the metadata doc (if any) for this onboarding_id.
    """
    return vectorstore_meta_coll.find_one({"onboarding_id": onboarding_id})

# ──────────────────────────────────────────────────────────────────────────────
# 5. Initialize (or Return) a MongoDBChatMessageHistory for chat_id
# ──────────────────────────────────────────────────────────────────────────────
def initialize_chat_history(chat_id: str) -> MongoDBChatMessageHistory:
    """
    Create and return a MongoDBChatMessageHistory for the given chat_id.
    """
    return MongoDBChatMessageHistory(
        session_id=chat_id,
        connection_string=settings.mongo_uri,
        database_name=settings.mongo_chat_db,
        collection_name=chat_collection_name,
    )

# ──────────────────────────────────────────────────────────────────────────────
# 6. Build a ConversationalRetrievalChain (RAG Chain) for onboarding_id + chat_id
# ──────────────────────────────────────────────────────────────────────────────
def build_rag_chain(onboarding_id: str, chat_id: str, prompt_type: str) -> ConversationalRetrievalChain:
    """
    - Loads the FAISS index for onboarding_id.
    - Creates a retriever (k=3).
    - Wraps MongoDBChatMessageHistory in a ConversationBufferMemory.
    - Attaches the ChatGroq LLM + user_prompt.
    """
    # 1. Load FAISS index (or 404 if not found)
    try:
        faiss_vs = build_or_load_vectorstore(onboarding_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Vectorstore not found for this onboarding_id. Call /rag/ingest first.")

    retriever = faiss_vs.as_retriever(search_kwargs={"k": 5})

    # 2. Instantiate a MongoDB-based chat history
    chat_history = initialize_chat_history(chat_id)

    # 3. Wrap that history in a ConversationBufferMemory, so the chain gets a valid "Memory" object
    memory = ConversationBufferMemory(
        memory_key="chat_history",    # how the chain will reference the stored chat messages
        chat_history=chat_history     # THIS tells the memory to use your MongoDB store
    )

    # 4. Get the LLM
    llm = get_llm()

    if prompt_type == "page_speed":
        # Use the specific prompt for Page Speed Insights
        user_prompt = page_speed_prompt
    elif prompt_type == "seo":
        # Use the specific prompt for SEO
        user_prompt = seo_prompt
    else:
        # Default to the user prompt if no specific type is provided
        user_prompt = default_user_prompt

    # 5. Build the ConversationalRetrievalChain with the wrapped memory
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,                             # ← pass the ConversationBufferMemory here
        return_source_documents=False,
        chain_type="stuff",
        combine_docs_chain_kwargs={"prompt": user_prompt},  # Use the user prompt for combining docs
        verbose=False,
    )
    return chain
