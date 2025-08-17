# # db.py
# from pymongo import MongoClient
# from app.page_speed.config import settings
#from qdrant_client import QdrantClient

# # ──────────────────────────────────────────────────────────────────────────────
# # MongoDB Initialization
# # ──────────────────────────────────────────────────────────────────────────────

# # Connect to MongoDB using the URI from settings
# mongo_client = MongoClient(settings.mongo_uri)

# # Use the renamed settings attributes
# mongo_db = mongo_client[settings.mongo_db]

# # Collection to store metadata that maps user_id → vectorstore_path
# vectorstore_meta_coll = mongo_db["vectorstore_metadata"]

# # Name of the collection that MongoDBChatMessageHistory will write to
# chat_collection_name = settings.mongo_collection

# # ─────────────────────────────────────────────
# # Qdrant Setup
# # ─────────────────────────────────────────────
# # If Qdrant is running locally
# qdrant_client = QdrantClient(
#     url=settings.qdrant_url,  # e.g. "http://localhost:6333"
#     api_key=settings.qdrant_api_key or None
# )

# ____________________________________________________________
#Local MongoDB Connection
# ____________________________________________________________

# db.py
from pymongo import MongoClient
from app.page_speed.config import settings
from qdrant_client import QdrantClient

# Always connect to local MongoDB
mongo_client = MongoClient("mongodb://localhost:27017/")

# Select the database from settings
mongo_db = mongo_client[settings.mongo_db]

# Collections
vectorstore_meta_coll = mongo_db["vectorstore_metadata"]
chat_collection_name = settings.mongo_collection

# ─────────────────────────────────────────────
# Qdrant Setup
# ─────────────────────────────────────────────
# If Qdrant is running locally
qdrant_client = QdrantClient(
    url=settings.qdrant_url,  # e.g. "http://localhost:6333"
    api_key=settings.qdrant_api_key or None
)