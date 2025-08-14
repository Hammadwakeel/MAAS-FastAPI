import os
from typing import Optional, Dict, Any
from fastapi import HTTPException

from langchain_community.vectorstores import FAISS
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain

from app.page_speed.config import settings
from .db import vectorstore_meta_coll, chat_collection_name
from .embeddings import embeddings, text_splitter, get_llm
from .logging_config import logger
from .prompt_library import (
    default_user_prompt,
    page_speed_prompt,
    seo_prompt,
    content_relevance_prompt,
    uiux_prompt,
    mobile_usability_prompt
)

# 1. Path with doc_type
def get_vectorstore_path(onboarding_id: str, doc_type: str) -> str:
    """
    Returns './vectorstores/{onboarding_id}/{doc_type}'.
    """
    base_dir = settings.vectorstore_base_path
    return os.path.join(base_dir, onboarding_id, doc_type)

# 2. Save to disk under doc_type
def save_vectorstore_to_disk(vectorstore: FAISS, onboarding_id: str, doc_type: str) -> str:
    """
    Save under './vectorstores/{onboarding_id}/{doc_type}/faiss_index'.
    """
    vs_dir = get_vectorstore_path(onboarding_id, doc_type)
    faiss_index_path = os.path.join(vs_dir, "faiss_index")
    os.makedirs(faiss_index_path, exist_ok=True)
    vectorstore.save_local(folder_path=faiss_index_path)
    return faiss_index_path

# 3. Metadata now includes doc_type
def upsert_vectorstore_metadata(
    onboarding_id: str,
    doc_type: str,
    vectorstore_path: str,
    chat_id: str
) -> None:
    vectorstore_meta_coll.update_one(
        {"onboarding_id": onboarding_id, "doc_type": doc_type},
        {"$set": {"vectorstore_path": vectorstore_path, "chat_id": chat_id}},
        upsert=True
    )


def get_vectorstore_metadata(
    onboarding_id: str,
    doc_type: str
) -> Optional[Dict[str, Any]]:
    return vectorstore_meta_coll.find_one({"onboarding_id": onboarding_id, "doc_type": doc_type})

# 4. Build chain now takes doc_type

def build_rag_chain(
    onboarding_id: str,
    doc_type: str,
    chat_id: str,
    prompt_type: str
) -> ConversationalRetrievalChain:
    # Load index
    vs_path = get_vectorstore_path(onboarding_id, doc_type)
    faiss_vs = FAISS.load_local(
        folder_path=os.path.join(vs_path, "faiss_index"),
        embeddings=embeddings,
        allow_dangerous_deserialization=True
    )
    retriever = faiss_vs.as_retriever(search_kwargs={"k": 5})

    # History & memory
    chat_history = MongoDBChatMessageHistory(
        session_id=chat_id,
        connection_string=settings.mongo_uri,
        database_name=settings.mongo_db,
        collection_name=chat_collection_name,
    )
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        chat_history=chat_history
    )

    llm = get_llm()
    # Choose prompt
    if prompt_type == "page_speed":
        user_prompt = page_speed_prompt
    elif prompt_type == "seo":
        user_prompt = seo_prompt
    elif prompt_type == "content_relevance":
        user_prompt = content_relevance_prompt
    elif prompt_type == "uiux":
        user_prompt = uiux_prompt
    elif prompt_type == "mobile_usability":
        user_prompt = mobile_usability_prompt
    else:
        user_prompt = default_user_prompt

    return ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=False,
        chain_type="stuff",
        combine_docs_chain_kwargs={"prompt": user_prompt},
        verbose=False
    )
