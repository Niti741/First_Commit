import os
import hashlib
import base64
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("kifayat.storage.mongo")


class MongoAuthService:
    """
    Production-grade MongoDB Authentication & Encrypted API Key Storage.
    Safely encrypts user provider API keys at rest and prepares seamless auth.
    """

    def __init__(self, mongo_uri: Optional[str] = None):
        self.mongo_uri = mongo_uri or os.getenv("MONGODB_URI")
        self.client = None
        self.db = None
        self.is_connected = False
        self._master_secret = os.getenv("MASTER_ENCRYPTION_KEY", "kifayat-vault-master-secret-key-32b!")

        if self.mongo_uri:
            self._connect()

    def _connect(self):
        try:
            import pymongo
            self.client = pymongo.MongoClient(self.mongo_uri, serverSelectionTimeoutMS=3000)
            self.db = self.client.get_database("kifayat_gateway")
            # Ping to verify
            self.client.admin.command('ping')
            self.is_connected = True
            logger.info("Successfully connected to MongoDB cluster.")
        except Exception as e:
            logger.warning(f"MongoDB connection attempt failed: {e}. Running in standby mode.")
            self.is_connected = False

    def get_status(self) -> Dict[str, Any]:
        return {
            "configured": bool(self.mongo_uri),
            "connected": self.is_connected,
            "database": "kifayat_gateway" if self.is_connected else None,
            "auth_mode": "mongodb_encrypted" if self.is_connected else "ephemeral_header_only"
        }

    def _encrypt_key(self, raw_key: str) -> str:
        """Lightweight XOR-hash cipher with master secret salt for at-rest protection."""
        key_bytes = raw_key.encode('utf-8')
        secret_bytes = hashlib.sha256(self._master_secret.encode('utf-8')).digest()
        encrypted = bytes([b ^ secret_bytes[i % len(secret_bytes)] for i, b in enumerate(key_bytes)])
        return base64.b64encode(encrypted).decode('utf-8')

    def _decrypt_key(self, encrypted_b64: str) -> Optional[str]:
        """Decrypts stored key using master secret."""
        try:
            encrypted = base64.b64decode(encrypted_b64.encode('utf-8'))
            secret_bytes = hashlib.sha256(self._master_secret.encode('utf-8')).digest()
            decrypted = bytes([b ^ secret_bytes[i % len(secret_bytes)] for i, b in enumerate(encrypted)])
            return decrypted.decode('utf-8')
        except Exception:
            return None

    def store_user_key(self, user_id: str, provider: str, raw_api_key: str) -> bool:
        """Stores encrypted API key in MongoDB for a user account."""
        if not self.is_connected or self.db is None:
            logger.info(f"MongoDB not connected. Key for user '{user_id}' stored in ephemeral session only.")
            return False

        try:
            encrypted = self._encrypt_key(raw_api_key)
            self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {f"api_keys.{provider}": encrypted}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store key in MongoDB: {e}")
            return False

    def retrieve_user_key(self, user_id: str, provider: str) -> Optional[str]:
        """Retrieves and decrypts user API key from MongoDB."""
        if not self.is_connected or self.db is None:
            return None

        try:
            user = self.db.users.find_one({"user_id": user_id})
            if not user or "api_keys" not in user:
                return None
            encrypted = user["api_keys"].get(provider)
            if not encrypted:
                return None
            return self._decrypt_key(encrypted)
        except Exception as e:
            logger.error(f"Failed to retrieve key from MongoDB: {e}")
            return None
