# app/rag/routes.py
"""
RAG FastAPI routes.

This file contains:
- /initialization/{onboarding_id}/{doc_type} : ingest documents and create a RAG session
- /chat/{onboarding_id}/{doc_type}/{chat_id} : perform a retrieval-augmented chat using stored vectorstore

The functions add additional logging to make debugging easier and to surface metrics:
- request start/finish times and durations
- counts and sizes (documents, chunks, vectors, batches)
- Qdrant operations and retries
- embedding function selection failures
"""
import os
import json
import uuid
import time
from typing import List, Optional, Iterable

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel

from .schemas import SetupRequest, ChatRequest, SetupResponse, ChatResponse
from .utils import (
    get_vectorstore_path,
    save_vectorstore_to_disk,
    upsert_vectorstore_metadata,
    get_vectorstore_metadata,
    build_rag_chain,
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
    Compute embeddings for a list of texts.

    Tries common bulk methods on the embeddings object and falls back to single-item calls.
    Logs which method is being attempted and any failures.
    """
    if not texts:
        logger.debug("_get_embeddings_for_texts called with empty texts list.")
        return []

    logger.debug("Computing embeddings for %d texts", len(texts))

    # Preferred bulk API methods to attempt
    for attr in ("embed_documents", "embed_texts", "embed_batch", "embed"):
        fn = getattr(embeddings, attr, None)
        if callable(fn):
            logger.debug("Trying embedding method: %s", attr)
            try:
                vecs = fn(texts)
                logger.debug("Embedding method %s returned %d vectors", attr, len(vecs) if vecs is not None else 0)
                return vecs
            except Exception:
                logger.debug("Embedding method %s failed; trying next option", attr, exc_info=True)

    # Fallback to single-item embedding function repeatedly
    single_fn = getattr(embeddings, "embed_query", None) or getattr(embeddings, "embed", None)
    if callable(single_fn):
        logger.debug("Falling back to single-item embedding function: %s", getattr(single_fn, "__name__", "<fn>"))
        vecs = []
        for i, t in enumerate(texts):
            try:
                vec = single_fn(t)
                if isinstance(vec, dict) and "embedding" in vec:
                    vecs.append(vec["embedding"])
                else:
                    vecs.append(vec)
            except Exception as e:
                logger.exception("Single-item embedding failed for text index %d: %s", i, e)
                raise
        logger.debug("Single-item embedding produced %d vectors", len(vecs))
        return vecs

    logger.error("Embeddings object does not expose a supported embedding method")
    raise RuntimeError(
        "Embeddings object does not expose a supported embedding method "
        "(embed_documents/embed_texts/embed_query/embed)."
    )


@router.post("/initialization/{onboarding_id}/{doc_type}", response_model=SetupResponse)
async def setup_rag_session(
    onboarding_id: str = Path(..., description="Unique onboarding identifier"),
    doc_type: str = Path(..., description="Type of document (e.g., page_speed, seo, content_relevance, uiux or mobile_usability)"),
    body: SetupRequest = ...,
):
    """
    Ingest documents under a specific document type and create a chat session.

    Behavior:
    - If vectorstore metadata exists for onboarding_id and doc_type in DB, skip ingestion (idempotent).
    - Always create a new chat_id for this session and return it.
    - Uses Qdrant as the vector store and stores metadata via upsert_vectorstore_metadata.

    Returns: SetupResponse
    """
    start_ts = time.time()
    logger.info("RAG initialization called for onboarding_id=%s doc_type=%s", onboarding_id, doc_type)

    try:
        # Use DB metadata instead of local filesystem marker
        existing_meta = get_vectorstore_metadata(onboarding_id, doc_type)
        if existing_meta:
            logger.info(
                "Vectorstore metadata exists for onboarding_id=%s, doc_type=%s; skipping ingestion",
                onboarding_id,
                doc_type,
            )
            metadata = existing_meta or {}
            chat_id = metadata.get("chat_id") or str(uuid.uuid4())
            if not ChatHistoryManager.chat_exists(chat_id):
                ChatHistoryManager.create_session(chat_id)
                logger.debug("Created new chat session for existing metadata chat_id=%s", chat_id)

            # ensure DB has chat_id (in case metadata existed but had missing fields)
            upsert_vectorstore_metadata(
                onboarding_id,
                doc_type,
                metadata.get("vectorstore_path"),
                chat_id,
                metadata.get("collection_name"),
            )

            duration = time.time() - start_ts
            logger.info("RAG initialization skipped ingestion (existing); duration=%.3fs", duration)
            return SetupResponse(
                success=True,
                message="RAG setup completed with existing vectorstore metadata.",
                onboarding_id=onboarding_id,
                doc_type=doc_type,
                chat_id=chat_id,
                vectorstore_path=metadata.get("vectorstore_path"),
            )

        # New ingestion flow
        if not body.documents:
            logger.error(
                "Missing documents for onboarding_id=%s, doc_type=%s",
                onboarding_id,
                doc_type,
            )
            raise HTTPException(status_code=400, detail="Please provide documents to ingest.")

        logger.info("Ingesting %d documents for %s/%s", len(body.documents), onboarding_id, doc_type)

        # Create session and ingest
        chat_id = str(uuid.uuid4())
        ChatHistoryManager.create_session(chat_id)
        logger.debug("Created chat session %s", chat_id)

        all_text = "\n\n".join(body.documents)
        text_chunks = text_splitter.split_text(all_text)
        logger.info("Split documents into %d text chunks", len(text_chunks))

        # Build Qdrant client from settings (with timeout + optional prefer_grpc)
        client_kwargs = {}
        if getattr(settings, "qdrant_url", None):
            client_kwargs["url"] = settings.qdrant_url
        if getattr(settings, "qdrant_api_key", None):
            client_kwargs["api_key"] = settings.qdrant_api_key

        qdrant_timeout = getattr(settings, "qdrant_timeout", 60)  # seconds (default 60)
        prefer_grpc = getattr(settings, "qdrant_prefer_grpc", False)

        try:
            if client_kwargs:
                qdrant_client = QdrantClient(**client_kwargs, timeout=qdrant_timeout, prefer_grpc=prefer_grpc)
                logger.debug("Instantiated QdrantClient with kwargs keys: %s", list(client_kwargs.keys()))
            else:
                qdrant_client = QdrantClient(timeout=qdrant_timeout, prefer_grpc=prefer_grpc)
                logger.debug("Instantiated QdrantClient with default connection (no url/api_key)")
        except TypeError as e:
            logger.exception("Failed to instantiate QdrantClient: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to construct Qdrant client: {e}")

        # Deterministic collection name for each onboarding/doc_type
        collection_name = f"vs_{onboarding_id}_{doc_type}"
        logger.info("Using Qdrant collection name: %s", collection_name)

        # --------------------------
        # INGEST: compute embeddings
        # --------------------------
        try:
            vectors = _get_embeddings_for_texts(text_chunks)
        except Exception as e:
            logger.exception("Failed to compute embeddings: %s", e)
            raise HTTPException(status_code=500, detail=f"Embedding error: {e}")

        if not vectors or len(vectors) != len(text_chunks):
            logger.error(
                "Embeddings length mismatch: vectors=%s texts=%s",
                len(vectors) if vectors is not None else None,
                len(text_chunks),
            )
            raise HTTPException(status_code=500, detail="Embedding generation failed or returned unexpected shape.")

        vector_size = len(vectors[0]) if vectors else 0
        logger.info("Computed embeddings: count=%d vector_size=%d", len(vectors), vector_size)
        if vector_size == 0:
            logger.error("Embedding returned empty vectors (vector_size=0)")
            raise HTTPException(status_code=500, detail="Embedding returned empty vectors")

        # Recreate collection (idempotent for onboarding+doc_type)
        try:
            qdrant_client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            logger.info("Recreated Qdrant collection %s (vector_size=%d)", collection_name, vector_size)
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
                    logger.debug("Safe upsert successful for %d points (collection=%s) on attempt %d", len(list(points)), collection_name, attempt + 1)
                    return
                except Exception as exc:
                    last_exc = exc
                    attempt += 1
                    logger.warning("Qdrant upsert attempt %d/%d failed: %s", attempt, max_retries, exc)
                    if attempt >= max_retries:
                        logger.exception("Qdrant upsert failed after %d attempts", max_retries)
                        raise
                    time.sleep(backoff)
                    backoff *= 2.0
            if last_exc:
                raise last_exc

        # Upsert points in smaller batches and use safe_upsert
        batch_size = getattr(settings, "qdrant_upsert_batch_size", 64)
        points_batch: List[PointStruct] = []
        total_points = 0
        try:
            for i, (vec, txt) in enumerate(zip(vectors, text_chunks)):
                payload = {"text": txt}
                point_id = str(uuid.uuid4())
                point = PointStruct(id=point_id, vector=vec, payload=payload)
                points_batch.append(point)
                total_points += 1

                if len(points_batch) >= batch_size:
                    logger.debug("Upserting batch of %d points to collection %s (processed=%d)", len(points_batch), collection_name, total_points)
                    safe_upsert(qdrant_client, collection_name, points_batch)
                    points_batch = []

            # final flush
            if points_batch:
                logger.debug("Upserting final batch of %d points to collection %s (processed=%d)", len(points_batch), collection_name, total_points)
                safe_upsert(qdrant_client, collection_name, points_batch)

            logger.info("Upserted total %d points into Qdrant collection %s", total_points, collection_name)
        except Exception as e:
            logger.exception("Failed to upsert points into qdrant: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to upsert points into Qdrant: {e}")

        # Create an in-application "vectorstore_path" (URI-style) and store metadata in DB
        try:
            vs_path = save_vectorstore_to_disk(
                onboarding_id,
                doc_type,
                collection_name,
                getattr(settings, "qdrant_url", None),
                getattr(settings, "qdrant_api_key", None),
            )
            logger.debug("Saved vectorstore metadata path: %s", vs_path)
        except Exception as e:
            logger.exception("Failed to save vectorstore metadata to disk/DB: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to persist vectorstore metadata: {e}")

        # Persist metadata into MongoDB (no local disk involved)
        try:
            upsert_vectorstore_metadata(onboarding_id, doc_type, vs_path, chat_id, collection_name)
            logger.info("Persisted vectorstore metadata for %s/%s (chat_id=%s)", onboarding_id, doc_type, chat_id)
        except Exception as e:
            logger.exception("Failed to upsert vectorstore metadata into DB: %s", e)
            raise HTTPException(status_code=500, detail=f"Failed to persist vectorstore metadata: {e}")

        duration = time.time() - start_ts
        logger.info(
            "Created Qdrant collection %s for %s/%s (points=%d) in %.3fs",
            collection_name,
            onboarding_id,
            doc_type,
            total_points,
            duration,
        )

        return SetupResponse(
            success=True,
            message="RAG setup completed.",
            onboarding_id=onboarding_id,
            doc_type=doc_type,
            chat_id=chat_id,
            vectorstore_path=vs_path,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (already logged above)
        raise
    except Exception as exc:
        logger.exception("Unhandled exception during RAG initialization for %s/%s: %s", onboarding_id, doc_type, exc)
        raise HTTPException(status_code=500, detail=f"Internal server error during RAG initialization: {exc}")


@router.post("/chat/{onboarding_id}/{doc_type}/{chat_id}", response_model=ChatResponse)
async def chat_with_user(
    onboarding_id: str = Path(...),
    doc_type: str = Path(...),
    chat_id: str = Path(...),
    prompt_type: str = Query(..., description="Prompt type, e.g., page_speed, content_relevance, seo, uiux or mobile_usability"),
    body: ChatRequest = ...,
):
    """
    Chat endpoint using a specific document-type vectorstore.

    Steps:
    - Verify vectorstore metadata exists.
    - Ensure chat session exists.
    - Optionally summarize history.
    - Build the RAG chain and invoke it with the question + chat_history.
    - Persist AI/human turns into ChatHistoryManager.
    """
    start_ts = time.time()
    logger.info("Chat request received: onboarding_id=%s doc_type=%s chat_id=%s prompt_type=%s", onboarding_id, doc_type, chat_id, prompt_type)

    try:
        # Use DB metadata instead of local filesystem marker
        metadata = get_vectorstore_metadata(onboarding_id, doc_type)
        if not metadata:
            logger.warning("Vectorstore metadata not found for %s/%s", onboarding_id, doc_type)
            raise HTTPException(status_code=400, detail="Vectorstore metadata not found; run initialization first.")

        if not ChatHistoryManager.chat_exists(chat_id):
            logger.warning("Chat session %s not found", chat_id)
            raise HTTPException(status_code=404, detail=f"Chat session {chat_id} not found.")

        question = (body.question or "").strip()
        if not question:
            logger.warning("Empty question in chat request for chat_id=%s", chat_id)
            raise HTTPException(status_code=400, detail="Question cannot be empty.")

        logger.info("Processing question (len=%d) for chat_id=%s", len(question), chat_id)
        ChatHistoryManager.summarize_if_needed(chat_id, threshold=10)
        ChatHistoryManager.add_message(chat_id, role="human", content=question)
        logger.debug("Added human message to history for chat_id=%s", chat_id)

        chain = build_rag_chain(onboarding_id, doc_type, chat_id, prompt_type)
        logger.debug("Built RAG chain for onboarding_id=%s doc_type=%s chat_id=%s", onboarding_id, doc_type, chat_id)

        history = ChatHistoryManager.get_messages(chat_id)
        logger.debug("Chat history length=%d for chat_id=%s", len(history), chat_id)

        try:
            result = chain.invoke({"question": question, "chat_history": history})
            logger.debug("RAG chain invoked successfully for chat_id=%s", chat_id)
        except Exception as e:
            logger.exception("RAG chain invocation failed for chat_id=%s: %s", chat_id, e)
            raise HTTPException(status_code=500, detail=f"RAG chain invocation failed: {e}")

        answer = result.get("answer") or result.get("output_text") or ""
        logger.info("Generated answer length=%d for chat_id=%s", len(answer), chat_id)
        ChatHistoryManager.add_message(chat_id, role="ai", content=answer)

        duration = time.time() - start_ts
        logger.info("Chat request completed for chat_id=%s duration=%.3fs", chat_id, duration)

        return ChatResponse(
            success=True,
            answer=answer,
            error=None,
            chat_id=chat_id,
            onboarding_id=onboarding_id,
            doc_type=doc_type,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (already logged above)
        raise
    except Exception as exc:
        logger.exception("Unhandled exception during chat for %s/%s chat_id=%s: %s", onboarding_id, doc_type, chat_id, exc)
        raise HTTPException(status_code=500, detail=f"Internal server error during chat: {exc}")
