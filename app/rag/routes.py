# app/rag/routes.py

import os
import json
import uuid
import time
from typing import List, Optional, Iterable

from fastapi import APIRouter, HTTPException, Path, Query

from .schemas import SetupRequest, ChatRequest, SetupResponse, ChatResponse
from .utils import (
    get_vectorstore_path,
    save_vectorstore_to_disk,
    upsert_vectorstore_metadata,
    get_vectorstore_metadata,
    build_rag_chain
)
from .chat_history import ChatHistoryManager
from .logging_config import logger

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, PointStruct, Distance
from app.page_speed.config import settings
from .embeddings import embeddings, text_splitter  # kept here for ingestion

router = APIRouter(prefix="/rag", tags=["rag"])


def _get_embeddings_for_texts(texts: List[str]) -> List[List[float]]:
    """
    Try common embedding API names (embed_documents, embed_texts, embed).
    Falls back to calling embed_query per text (slower).
    """
    if not texts:
        return []

    # Preferred bulk API
    for attr in ("embed_documents", "embed_texts", "embed_batch", "embed"):
        fn = getattr(embeddings, attr, None)
        if callable(fn):
            try:
                return fn(texts)
            except Exception:
                logger.debug("Embedding method %s failed; trying next option", attr, exc_info=True)

    # Fallback: try single-item embedding function repeatedly
    single_fn = getattr(embeddings, "embed_query", None) or getattr(embeddings, "embed", None)
    if callable(single_fn):
        vecs = []
        for t in texts:
            vec = single_fn(t)
            if isinstance(vec, dict) and "embedding" in vec:
                vecs.append(vec["embedding"])
            else:
                vecs.append(vec)
        return vecs

    raise RuntimeError(
        "Embeddings object does not expose a supported embedding method "
        "(embed_documents/embed_texts/embed_query)."
    )


@router.post("/initialization/{onboarding_id}/{doc_type}", response_model=SetupResponse)
async def setup_rag_session(
    onboarding_id: str = Path(..., description="Unique onboarding identifier"),
    doc_type: str = Path(..., description="Type of document (e.g., page_speed, seo, content_relevance, uiux or mobile_usability)"),
    body: SetupRequest = ...
):
    """
    Ingest documents under a specific document type and create a chat session.
    - If vectorstore metadata exists for onboarding_id and doc_type in MongoDB, skip ingestion.
    - Always create a new chat_id for this session.
    NOTE: This implementation does NOT create or rely on any local files on disk for metadata.
    """
    # Use DB metadata instead of local filesystem marker
    existing_meta = get_vectorstore_metadata(onboarding_id, doc_type)
    if existing_meta:
        logger.info(
            "Vectorstore metadata exists for onboarding_id=%s, doc_type=%s; skipping ingestion",
            onboarding_id, doc_type
        )
        metadata = existing_meta
        if metadata and metadata.get("chat_id"):
            chat_id = metadata["chat_id"]
        else:
            chat_id = str(uuid.uuid4())
            ChatHistoryManager.create_session(chat_id)
            # ensure DB has chat_id
            upsert_vectorstore_metadata(onboarding_id, doc_type, metadata.get("vectorstore_path"), chat_id, metadata.get("collection_name"))
        return SetupResponse(
            success=True,
            message="RAG setup completed with existing vectorstore metadata.",
            onboarding_id=onboarding_id,
            doc_type=doc_type,
            chat_id=chat_id,
            vectorstore_path=metadata.get("vectorstore_path")
        )

    # New ingestion flow
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

    # Build Qdrant client from settings (with timeout + optional prefer_grpc)
    client_kwargs = {}
    if getattr(settings, "qdrant_url", None):
        client_kwargs["url"] = settings.qdrant_url
    if getattr(settings, "qdrant_api_key", None):
        client_kwargs["api_key"] = settings.qdrant_api_key

    # sensible defaults; override via app config
    qdrant_timeout = getattr(settings, "qdrant_timeout", 60)        # seconds (default 60)
    prefer_grpc = getattr(settings, "qdrant_prefer_grpc", False)    # set True to use gRPC if available

    try:
        if client_kwargs:
            qdrant_client = QdrantClient(**client_kwargs, timeout=qdrant_timeout, prefer_grpc=prefer_grpc)
        else:
            qdrant_client = QdrantClient(timeout=qdrant_timeout, prefer_grpc=prefer_grpc)
    except TypeError as e:
        logger.exception("Failed to instantiate QdrantClient: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to construct Qdrant client: {e}")

    # Deterministic collection name for each onboarding/doc_type
    collection_name = f"vs_{onboarding_id}_{doc_type}"

    # --------------------------
    # INGEST: compute embeddings
    # --------------------------
    try:
        vectors = _get_embeddings_for_texts(text_chunks)
    except Exception as e:
        logger.exception("Failed to compute embeddings: %s", e)
        raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

    if not vectors or len(vectors) != len(text_chunks):
        logger.error("Embeddings length mismatch: vectors=%s texts=%s", len(vectors), len(text_chunks))
        raise HTTPException(status_code=500, detail="Embedding generation failed or returned unexpected shape.")

    vector_size = len(vectors[0])
    if vector_size == 0:
        raise HTTPException(status_code=500, detail="Embedding returned empty vectors")

    # Recreate collection (idempotent for onboarding+doc_type)
    try:
        qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
    except Exception as e:
        logger.exception("Failed to create/recreate qdrant collection '%s': %s", collection_name, e)
        raise HTTPException(status_code=500, detail=f"Failed to create qdrant collection: {e}")

    # Helper: safe upsert with retries/backoff
    def safe_upsert(client: QdrantClient, collection_name: str, points: Iterable[PointStruct], max_retries: int = 3):
        attempt = 0
        backoff = 1.0
        last_exc: Optional[Exception] = None
        while attempt < max_retries:
            try:
                client.upsert(collection_name=collection_name, points=points)
                return
            except Exception as exc:
                last_exc = exc
                attempt += 1
                logger.warning("Qdrant upsert attempt %d/%d failed: %s", attempt, max_retries, exc)
                if attempt >= max_retries:
                    logger.exception("Qdrant upsert failed after %d attempts", max_retries)
                    raise
                # exponential backoff
                time.sleep(backoff)
                backoff *= 2.0
        # if loop finishes without returning, raise last exception
        if last_exc:
            raise last_exc

    # Upsert points in smaller batches and use safe_upsert
    batch_size = getattr(settings, "qdrant_upsert_batch_size", 64)  # smaller default batch size
    points_batch: List[PointStruct] = []
    try:
        for i, (vec, txt) in enumerate(zip(vectors, text_chunks)):
            payload = {"text": txt}
            # Use UUID string for id to avoid collisions across sessions
            point_id = str(uuid.uuid4())
            point = PointStruct(id=point_id, vector=vec, payload=payload)
            points_batch.append(point)

            if len(points_batch) >= batch_size:
                logger.debug("Upserting batch of %d points to collection %s", len(points_batch), collection_name)
                safe_upsert(qdrant_client, collection_name, points_batch)
                points_batch = []

        # final flush
        if points_batch:
            logger.debug("Upserting final batch of %d points to collection %s", len(points_batch), collection_name)
            safe_upsert(qdrant_client, collection_name, points_batch)
    except Exception as e:
        logger.exception("Failed to upsert points into qdrant: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to upsert points into Qdrant: {e}")

    # Create an in-application "vectorstore_path" (URI-style) and store metadata in DB
    vs_path = save_vectorstore_to_disk(
        onboarding_id,
        doc_type,
        collection_name,
        getattr(settings, "qdrant_url", None),
        getattr(settings, "qdrant_api_key", None)
    )
    # Persist metadata into MongoDB (no local disk involved)
    # Persist extra metadata fields so retrieval can use same connection details (if desired)
    upsert_vectorstore_metadata(onboarding_id, doc_type, vs_path, chat_id, collection_name)

    logger.info(
        "Created Qdrant collection %s for %s/%s (points=%d)",
        collection_name, onboarding_id, doc_type, len(text_chunks)
    )

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
    prompt_type: str = Query(..., description="Prompt type, e.g., page_speed, content_relevance, seo, uiux or mobile_usability"),
    body: ChatRequest = ...
):
    """
    Chat endpoint using a specific document-type vectorstore.
    """
    # Use DB metadata instead of local filesystem marker
    metadata = get_vectorstore_metadata(onboarding_id, doc_type)
    if not metadata:
        raise HTTPException(status_code=400, detail="Vectorstore metadata not found; run initialization first.")

    if not ChatHistoryManager.chat_exists(chat_id):
        raise HTTPException(status_code=404, detail=f"Chat session {chat_id} not found.")

    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    ChatHistoryManager.summarize_if_needed(chat_id, threshold=10)
    ChatHistoryManager.add_message(chat_id, role="human", content=question)

    chain = build_rag_chain(onboarding_id, doc_type, chat_id, prompt_type)
    history = ChatHistoryManager.get_messages(chat_id)
    result = chain.invoke({"question": question, "chat_history": history})
    answer = result.get("answer") or result.get("output_text") or ""
    ChatHistoryManager.add_message(chat_id, role="ai", content=answer)

    return ChatResponse(
        success=True,
        answer=answer,
        error=None,
        chat_id=chat_id,
        onboarding_id=onboarding_id,
        doc_type=doc_type
    )
