# db.py
from pymongo import MongoClient
from app.page_speed.config import settings

# ──────────────────────────────────────────────────────────────────────────────
# MongoDB Initialization
# ──────────────────────────────────────────────────────────────────────────────

# Connect to MongoDB using the URI from settings
mongo_client = MongoClient(settings.mongo_uri)

# Use the renamed settings attributes
mongo_db = mongo_client[settings.mongo_db]

# Collection to store metadata that maps user_id → vectorstore_path
vectorstore_meta_coll = mongo_db["vectorstore_metadata"]

# Name of the collection that MongoDBChatMessageHistory will write to
chat_collection_name = settings.mongo_collection
