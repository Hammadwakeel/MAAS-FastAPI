import os
import uuid
from fastapi import APIRouter, HTTPException

from .schemas import SetupRequest, ChatRequest, SetupResponse, ChatResponse
from .utils import (
    text_splitter,
    embeddings,
    save_vectorstore_to_disk,
    upsert_vectorstore_metadata,
    get_vectorstore_path,
    build_rag_chain
)
from .chat_history import ChatHistoryManager
from .logging_config import logger

router = APIRouter(prefix="/rag", tags=["rag"])

@router.post("/initialization/{onboarding_id}", response_model=SetupResponse)
async def setup_rag_session(onboarding_id: str, body: SetupRequest):
    """
    Single endpoint to ingest documents and create a chat session.
    - If vectorstore exists for user_id, skip ingestion.
    - Always create a new chat_id for this session.
    """
    # 1. Handle vectorstore existence
    vectorstore_path = get_vectorstore_path(onboarding_id)
    if os.path.isdir(vectorstore_path):
        logger.info(
            "Vectorstore exists for onboarding_id=%s at %s; skipping ingestion",
            onboarding_id, vectorstore_path
        )
        vs_path = vectorstore_path
    else:
        if not body.documents:
            logger.error(
                "Vectorstore missing for onboarding_id=%s and no documents provided", onboarding_id
            )
            raise HTTPException(
                status_code=400,
                detail="Vectorstore does not exist; please provide documents to ingest."
            )
        # Ingest new vectorstore
        all_text = "\n\n".join(body.documents)
        text_chunks = text_splitter.split_text(all_text)
        logger.info("Split into %d chunks for ingestion", len(text_chunks))
        from langchain.vectorstores import FAISS as _FAISS
        vs = _FAISS.from_texts(texts=text_chunks, embedding=embeddings)
        vs_path = save_vectorstore_to_disk(vs, onboarding_id)
        logger.info("Saved FAISS index to %s", vs_path)
        upsert_vectorstore_metadata(onboarding_id, vs_path)
        logger.info(
            "Upserted vectorstore metadata for onboarding_id=%s", onboarding_id
        )

    # Create new chat session
    chat_id = str(uuid.uuid4())
    ChatHistoryManager.create_session(chat_id)
    logger.info(
        "Created new chat session %s for onboarding_id=%s",
        chat_id, onboarding_id
    )

    return SetupResponse(
        success=True,
        message="RAG setup completed.",
        onboarding_id=onboarding_id,
        chat_id=chat_id,
        vectorstore_path=vs_path
    )

@router.post("/chat/{onboarding_id}/{chat_id}", response_model=ChatResponse)
async def chat_with_user(onboarding_id: str, chat_id: str, prompt_type: str, body: ChatRequest):
    """
    Chat endpoint that uses an existing chat session and vectorstore.
    - Validates that the vectorstore exists for onboarding_id.
    - Validates that the chat session exists.
    """
    # 0. Validate vectorstore
    vectorstore_path = get_vectorstore_path(onboarding_id)
    if not os.path.isdir(vectorstore_path):
        logger.error("Vectorstore not found for onboarding_id=%s", onboarding_id)
        raise HTTPException(
            status_code=400,
            detail="Vectorstore not found for this onboarding_id. Please run /setup first."
        )

    # 1. Ensure chat session exists
    if not ChatHistoryManager.chat_exists(chat_id):
        logger.error("Chat session %s not found for onboarding_id=%s", chat_id, onboarding_id)
        raise HTTPException(
            status_code=404,
            detail=f"Chat session {chat_id} does not exist."
        )

    question = body.question.strip()
    logger.info("Chat request onboarding_id=%s chat=%s question=%s", onboarding_id, chat_id, question)

    try:
        # Summarize long histories
        ChatHistoryManager.summarize_if_needed(chat_id, threshold=10)

        # Record the user message
        ChatHistoryManager.add_message(chat_id, role="human", content=question)

        # Build and invoke the RAG chain
        chain = build_rag_chain(onboarding_id, chat_id, prompt_type)
        history = ChatHistoryManager.get_messages(chat_id)
        result = chain.invoke({"question": question, "chat_history": history})
        answer = result.get("answer") or result.get("output_text")
        if not answer:
            raise Exception("No answer returned from chain")

        # Record the AI response
        ChatHistoryManager.add_message(chat_id, role="ai", content=answer)

        return ChatResponse(
            success=True,
            answer=answer,
            error=None,
            chat_id=chat_id,
            onboarding_id=onboarding_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error chatting onboarding_id=%s chat=%s: %s", onboarding_id, chat_id, e, exc_info=True)
        return ChatResponse(
            success=False,
            answer=None,
            error=str(e),
            chat_id=chat_id,
            onboarding_id=onboarding_id
        )
