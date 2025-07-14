import os
import uuid
from fastapi import APIRouter, HTTPException, Path, Query

from .schemas import SetupRequest, ChatRequest, SetupResponse, ChatResponse
from .utils import (
    get_vectorstore_path,
    text_splitter,
    embeddings,
    save_vectorstore_to_disk,
    upsert_vectorstore_metadata,
    get_vectorstore_metadata,
    build_rag_chain
)
from .chat_history import ChatHistoryManager
from .logging_config import logger

router = APIRouter(prefix="/rag", tags=["rag"])

@router.post("/initialization/{onboarding_id}/{doc_type}", response_model=SetupResponse)
async def setup_rag_session(
    onboarding_id: str = Path(..., description="Unique onboarding identifier"),
    doc_type: str = Path(..., description="Type of document (e.g., page_speed, seo, uiux)"),
    body: SetupRequest = ...
):
    """
    Ingest documents under a specific document type and create a chat session.
    - If vectorstore exists for onboarding_id and doc_type, skip ingestion.
    - Always create a new chat_id for this session.
    """
    vectorstore_path = get_vectorstore_path(onboarding_id, doc_type)

    # Existing vectorstore
    if os.path.isdir(os.path.join(vectorstore_path, "faiss_index")):
        logger.info(
            "Vectorstore exists for onboarding_id=%s, doc_type=%s; skipping ingestion",
            onboarding_id, doc_type
        )
        metadata = get_vectorstore_metadata(onboarding_id, doc_type)
        if metadata and metadata.get("chat_id"):
            chat_id = metadata["chat_id"]
        else:
            chat_id = str(uuid.uuid4())
            ChatHistoryManager.create_session(chat_id)
            upsert_vectorstore_metadata(onboarding_id, doc_type, vectorstore_path, chat_id)
        return SetupResponse(
            success=True,
            message="RAG setup completed with existing vectorstore.",
            onboarding_id=onboarding_id,
            doc_type=doc_type,
            chat_id=chat_id,
            vectorstore_path=vectorstore_path
        )

    # New ingestion
    if not body.documents:
        logger.error(
            "Missing documents for onboarding_id=%s, doc_type=%s",
            onboarding_id, doc_type
        )
        raise HTTPException(status_code=400, detail="Please provide documents to ingest.")

    # Create session and ingest
    chat_id = str(uuid.uuid4())
    ChatHistoryManager.create_session(chat_id)
    all_text = "\n\n".join(body.documents)
    text_chunks = text_splitter.split_text(all_text)
    vs = __import__("langchain_community.vectorstores").vectorstores.FAISS.from_texts(
        texts=text_chunks,
        embedding=embeddings
    )
    vs_path = save_vectorstore_to_disk(vs, onboarding_id, doc_type)
    upsert_vectorstore_metadata(onboarding_id, doc_type, vs_path, chat_id)

    return SetupResponse(
        success=True,
        message="RAG setup completed.",
        onboarding_id=onboarding_id,
        doc_type=doc_type,
        chat_id=chat_id,
        vectorstore_path=vs_path
    )

@router.post("/chat/{onboarding_id}/{doc_type}/{chat_id}", response_model=ChatResponse)
async def chat_with_user(
    onboarding_id: str = Path(...),
    doc_type: str = Path(...),
    chat_id: str = Path(...),
    prompt_type: str = Query(..., description="Prompt type, e.g., page_speed or seo"),
    body: ChatRequest = ...
):
    """
    Chat endpoint using a specific document-type vectorstore.
    """
    vectorstore_path = get_vectorstore_path(onboarding_id, doc_type)
    if not os.path.isdir(os.path.join(vectorstore_path, "faiss_index")):
        raise HTTPException(status_code=400, detail="Vectorstore not found; run initialization first.")

    if not ChatHistoryManager.chat_exists(chat_id):
        raise HTTPException(status_code=404, detail=f"Chat session {chat_id} not found.")

    question = body.question.strip()
    ChatHistoryManager.summarize_if_needed(chat_id, threshold=10)
    ChatHistoryManager.add_message(chat_id, role="human", content=question)

    chain = build_rag_chain(onboarding_id, doc_type, chat_id, prompt_type)
    history = ChatHistoryManager.get_messages(chat_id)
    result = chain.invoke({"question": question, "chat_history": history})
    answer = result.get("answer") or result.get("output_text")
    ChatHistoryManager.add_message(chat_id, role="ai", content=answer)

    return ChatResponse(
        success=True,
        answer=answer,
        error=None,
        chat_id=chat_id,
        onboarding_id=onboarding_id,
        doc_type=doc_type
    )