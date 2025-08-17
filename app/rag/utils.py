# app/rag/utils.py

import os
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import HTTPException

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document

from pydantic import ConfigDict  # Pydantic v2 config for BaseModel-based classes

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


# ──────────────────────────────────────────────────────────────────────────────
# Paths & metadata helpers (diskless)
# ──────────────────────────────────────────────────────────────────────────────

def get_vectorstore_path(onboarding_id: str, doc_type: str) -> str:
    """
    Returns a non-disk URI-like path for a vectorstore.
    Example: 'qdrant://<onboarding_id>/<doc_type>'
    This avoids creating a local folder while preserving a string that identifies
    the logical vectorstore for other components and logs.
    """
    return f"qdrant://{onboarding_id}/{doc_type}"


def save_vectorstore_to_disk(
    onboarding_id: str,
    doc_type: str,
    collection_name: str,
    qdrant_url: Optional[str],
    qdrant_api_key: Optional[str]
) -> str:
    """
    Previously this created a small local marker file with Qdrant connection details.
    In the diskless version we simply return a logical vectorstore path (URI-style).
    Persisting of metadata is done via `upsert_vectorstore_metadata`.
    """
    vs_path = get_vectorstore_path(onboarding_id, doc_type)
    return vs_path


def upsert_vectorstore_metadata(
    onboarding_id: str,
    doc_type: str,
    vectorstore_path: str,
    chat_id: str,
    collection_name: Optional[str] = None,
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None
) -> None:
    """
    Store metadata in MongoDB. Saves useful fields to allow build_rag_chain to
    reconstruct a working Qdrant client later.
    """
    update = {
        "onboarding_id": onboarding_id,
        "doc_type": doc_type,
        "vectorstore_path": vectorstore_path,
        "chat_id": chat_id,
        "updated_at": datetime.utcnow(),
    }
    if collection_name:
        update["collection_name"] = collection_name
    if qdrant_url:
        update["qdrant_url"] = qdrant_url
    if qdrant_api_key:
        update["qdrant_api_key"] = qdrant_api_key

    # Upsert the document
    vectorstore_meta_coll.update_one(
        {"onboarding_id": onboarding_id, "doc_type": doc_type},
        {"$set": update, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True
    )
    logger.debug("Upserted vectorstore metadata for %s/%s into Mongo", onboarding_id, doc_type)


def get_vectorstore_metadata(
    onboarding_id: str,
    doc_type: str
) -> Optional[Dict[str, Any]]:
    """
    Read vectorstore metadata from MongoDB (no local files).
    """
    meta = vectorstore_meta_coll.find_one({"onboarding_id": onboarding_id, "doc_type": doc_type})
    if meta:
        # convert ObjectId or other non-serializable fields if necessary
        return meta
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Qdrant Retriever (pure Qdrant, Pydantic v2-compatible)
# ──────────────────────────────────────────────────────────────────────────────

class QdrantTextRetriever(BaseRetriever):
    """
    Minimal retriever that queries Qdrant directly and returns LangChain Documents.
    Assumes payload stores the raw chunk under key 'text'.
    """

    client: QdrantClient
    collection_name: str
    k: int = 5
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        # Embed the query. Try multiple attribute names safely.
        query_vec = None
        for attr in ("embed_query", "embed_documents", "embed_texts", "embed"):
            fn = getattr(embeddings, attr, None)
            if callable(fn):
                try:
                    if attr == "embed_query":
                        query_vec = fn(query)
                    else:
                        q_res = fn([query])
                        if isinstance(q_res, list) and q_res:
                            query_vec = q_res[0]
                        else:
                            query_vec = q_res
                    break
                except Exception:
                    continue
        if query_vec is None:
            raise RuntimeError("No usable embedding function available on embeddings object.")

        # If embedding helpers return dicts
        if isinstance(query_vec, dict) and "embedding" in query_vec:
            query_vec = query_vec["embedding"]

        # Search Qdrant
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vec,
            limit=self.k
        )

        docs: List[Document] = []
        for r in results:
            payload = r.payload or {}
            text = payload.get("text")
            if not isinstance(text, str):
                logger.warning(
                    "Qdrant payload missing 'text' or not a string; skipping. Payload: %s",
                    payload
                )
                continue

            metadata = {k: v for k, v in payload.items() if k != "text"}
            metadata["score"] = r.score

            docs.append(Document(page_content=text, metadata=metadata))

        return docs

    async def _aget_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        # For simplicity, use sync path
        return self._get_relevant_documents(query, run_manager=run_manager)


# ──────────────────────────────────────────────────────────────────────────────
# Build RAG chain (pure Qdrant), using DB metadata (no local files)
# ──────────────────────────────────────────────────────────────────────────────

def build_rag_chain(
    onboarding_id: str,
    doc_type: str,
    chat_id: str,
    prompt_type: str
) -> ConversationalRetrievalChain:
    """
    Builds a ConversationalRetrievalChain using pure Qdrant as backend.
    Loads connection details from the MongoDB metadata collection instead of a file.
    If metadata is missing, tries to detect an existing Qdrant collection named
    'vs_{onboarding_id}_{doc_type}' and auto-registers it in Mongo.
    """
    meta = get_vectorstore_metadata(onboarding_id, doc_type)

    # If metadata missing — attempt a Qdrant-side fallback detection
    if not meta:
        logger.warning("Vectorstore metadata not found for %s/%s in Mongo; attempting Qdrant fallback detection", onboarding_id, doc_type)

        # Build a Qdrant client from global settings to detect existing collection
        qdrant_url = getattr(settings, "qdrant_url", None)
        qdrant_api_key = getattr(settings, "qdrant_api_key", None)
        client_kwargs = {}
        if qdrant_url:
            client_kwargs["url"] = qdrant_url
        if qdrant_api_key:
            client_kwargs["api_key"] = qdrant_api_key

        qdrant_timeout = getattr(settings, "qdrant_timeout", 60)
        prefer_grpc = getattr(settings, "qdrant_prefer_grpc", False)

        try:
            if client_kwargs:
                qdrant_client = QdrantClient(**client_kwargs, timeout=qdrant_timeout, prefer_grpc=prefer_grpc)
            else:
                qdrant_client = QdrantClient(timeout=qdrant_timeout, prefer_grpc=prefer_grpc)
        except Exception as e:
            logger.exception("Failed to create Qdrant client during fallback detection: %s", e)
            raise HTTPException(status_code=500, detail="Vectorstore metadata not found and failed to connect to Qdrant for fallback detection.")

        guessed_collection = f"vs_{onboarding_id}_{doc_type}"
        try:
            # get_collection raises if not present; get_collections returns list
            info = None
            try:
                info = qdrant_client.get_collection(collection_name=guessed_collection)
            except Exception:
                # try listing collections (less strict)
                collections_info = qdrant_client.get_collections()
                # get_collections returns a dict-like structure; search names
                found = False
                for c in collections_info.get("collections", []) if isinstance(collections_info, dict) else collections_info:
                    name = c.get("name") if isinstance(c, dict) else getattr(c, "name", None)
                    if name == guessed_collection:
                        found = True
                        break
                if not found:
                    info = None
                else:
                    info = {"name": guessed_collection}

            if info:
                logger.info("Detected existing Qdrant collection '%s' via fallback; auto-registering metadata in Mongo", guessed_collection)
                # auto-register minimal metadata so chat can proceed
                vs_path = get_vectorstore_path(onboarding_id, doc_type)
                # we don't have a chat_id to store here; store empty string and let setup create chat sessions later
                upsert_vectorstore_metadata(onboarding_id, doc_type, vs_path, chat_id="", collection_name=guessed_collection, qdrant_url=qdrant_url, qdrant_api_key=qdrant_api_key)
                meta = get_vectorstore_metadata(onboarding_id, doc_type)
            else:
                logger.info("Qdrant fallback detection found no collection named '%s'", guessed_collection)
        except Exception as e:
            logger.exception("Error while checking Qdrant collections for fallback detection: %s", e)
            # continue; meta still None and we'll raise below

    if not meta:
        # Final: helpful error message with actionable next steps
        raise HTTPException(
            status_code=400,
            detail=(
                "Vectorstore metadata not found; run initialization first. "
                "Call POST /rag/initialization/{onboarding_id}/{doc_type} with documents to ingest. "
                "If you already initialized, check server logs for ingestion errors and verify Mongo collection "
                "'vectorstore_meta_coll' contains the record for this onboarding/doc_type."
            )
        )

    collection_name = meta.get("collection_name")
    if not collection_name:
        raise HTTPException(status_code=500, detail="Qdrant collection name missing in metadata.")

    # Prefer values from marker; fall back to app settings if needed
    qdrant_url = meta.get("qdrant_url") or getattr(settings, "qdrant_url", None)
    qdrant_api_key = meta.get("qdrant_api_key") or getattr(settings, "qdrant_api_key", None)

    client_kwargs = {}
    if qdrant_url:
        client_kwargs["url"] = qdrant_url
    if qdrant_api_key:
        client_kwargs["api_key"] = qdrant_api_key

    qdrant_timeout = getattr(settings, "qdrant_timeout", 60)
    prefer_grpc = getattr(settings, "qdrant_prefer_grpc", False)

    try:
        if client_kwargs:
            qdrant_client = QdrantClient(**client_kwargs, timeout=qdrant_timeout, prefer_grpc=prefer_grpc)
        else:
            qdrant_client = QdrantClient(timeout=qdrant_timeout, prefer_grpc=prefer_grpc)
    except Exception as e:
        logger.exception("Failed to construct Qdrant client for retrieval: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to connect to Qdrant: {e}")

    retriever = QdrantTextRetriever(client=qdrant_client, collection_name=collection_name, k=5)

    # History & memory
    chat_history = MongoDBChatMessageHistory(
        session_id=chat_id,
        connection_string=settings.mongo_uri,
        database_name=settings.mongo_db,
        collection_name=chat_collection_name,
    )
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=chat_history,
        return_messages=True,
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
