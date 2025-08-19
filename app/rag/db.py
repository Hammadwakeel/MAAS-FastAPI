# app/db.py
import time
import logging
from typing import Optional

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
import certifi
from qdrant_client import QdrantClient  # Add this import

from app.page_speed.config import settings

logger = logging.getLogger(__name__)
# Configure logger if root logger not configured by app
if not logging.getLogger().handlers:
    # Basic configuration for standalone testing; in real app your main config may override this.
    logging.basicConfig(level=logging.INFO)

# Tunable timeout (ms)
MONGO_SERVER_SELECTION_TIMEOUT_MS = 20000  # 20 seconds

def _create_mongo_client() -> MongoClient:
    """
    Create and return a MongoClient configured to use TLS with certifi CA bundle.
    This function intentionally passes tls=True and tlsCAFile to make TLS explicit and reliable.
    """
    uri = settings.mongo_uri
    logger.info("Creating MongoClient for URI: %s", uri)

    try:
        client = MongoClient(
            uri,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=MONGO_SERVER_SELECTION_TIMEOUT_MS,
        )
        logger.debug("MongoClient created with explicit TLS and certifi CA bundle.")
        return client
    except TypeError as e:
        # In case an older pymongo version doesn't accept tls* keywords (unlikely if pymongo[srv] is installed)
        logger.warning("MongoClient creation with tls arguments failed (%s). Falling back without tls args.", e)
        client = MongoClient(uri, serverSelectionTimeoutMS=MONGO_SERVER_SELECTION_TIMEOUT_MS)
        return client
    except Exception as e:
        logger.exception("Unexpected exception while creating MongoClient: %s", e)
        raise

# Instantiate client and perform startup connectivity check (ping) with retries
mongo_client: Optional[MongoClient] = None
_last_exc: Optional[Exception] = None

try:
    mongo_client = _create_mongo_client()
    # Retry ping a few times to get useful logs for TLS failures
    for attempt in range(1, 4):
        try:
            logger.info("Pinging MongoDB (attempt %d)...", attempt)
            mongo_client.admin.command("ping")
            logger.info("Successfully connected to MongoDB.")
            _last_exc = None
            break
        except ServerSelectionTimeoutError as e:
            _last_exc = e
            logger.exception("ServerSelectionTimeoutError pinging MongoDB on attempt %d: %s", attempt, e)
        except ConfigurationError as e:
            _last_exc = e
            logger.exception("ConfigurationError pinging MongoDB: %s", e)
            break
        except Exception as e:
            _last_exc = e
            logger.exception("Unexpected error pinging MongoDB on attempt %d: %s", attempt, e)
        time.sleep(1 * attempt)
except Exception as e:
    _last_exc = e
    logger.exception("MongoClient creation failed: %s", e)

if _last_exc:
    # Fail fast — raising here prevents the app from running in a broken state.
    # If you prefer not to raise in development, replace `raise` with `logger.error(...)` and continue.
    raise _last_exc

# Select DB and collections
mongo_db = mongo_client[settings.mongo_db]
vectorstore_meta_coll = mongo_db["vectorstore_metadata"]
chat_collection_name = settings.mongo_collection

def get_mongo_client() -> MongoClient:
    """Return the active MongoClient instance."""
    return mongo_client

def get_vectorstore_collection():
    return vectorstore_meta_coll

# ─────────────────────────────────────────────
# Qdrant Setup
# ─────────────────────────────────────────────
# If Qdrant is running locally
qdrant_client = QdrantClient(
    url=settings.qdrant_url,  # e.g. "http://localhost:6333"
    api_key=settings.qdrant_api_key or None
)

# # ____________________________________________________________
# #Local MongoDB Connection
# # ____________________________________________________________

# # db.py
# from pymongo import MongoClient
# from app.page_speed.config import settings
# from qdrant_client import QdrantClient

# # Always connect to local MongoDB
# mongo_client = MongoClient("mongodb://localhost:27017/")

# # Select the database from settings
# mongo_db = mongo_client[settings.mongo_db]

# # Collections
# vectorstore_meta_coll = mongo_db["vectorstore_metadata"]
# chat_collection_name = settings.mongo_collection

# # ─────────────────────────────────────────────
# # Qdrant Setup
# # ─────────────────────────────────────────────
# # If Qdrant is running locally
# qdrant_client = QdrantClient(
#     url=settings.qdrant_url,  # e.g. "http://localhost:6333"
#     api_key=settings.qdrant_api_key or None
# )