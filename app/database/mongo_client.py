"""
MongoDB Database Driver and Client Helper for Pharmavigil
Manages PyMongo connections, collection access, and database exceptions.
"""

from typing import Optional
import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError, ConnectionFailure

from app.config import config
from app.utils.exceptions import DatabaseConnectionError


class MongoDBClient:
    """Encapsulates MongoDB connection management and collection access."""

    def __init__(self):
        self.uri = config.mongo.uri
        self.db_name = config.mongo.database
        self.adverse_collection_name = config.mongo.adverse_collection
        self._client: Optional[MongoClient] = None

    def get_client(self) -> MongoClient:
        """Returns active MongoClient or initializes a new connection pool."""
        if self._client is None:
            try:
                self._client = MongoClient(
                    self.uri,
                    serverSelectionTimeoutMS=3000,
                    connectTimeoutMS=3000
                )
                # Verify connection liveness
                self._client.admin.command('ping')
            except (ConnectionFailure, PyMongoError) as err:
                self._client = None
                raise DatabaseConnectionError(
                    f"MongoDB Connection Error on {self.uri}: {str(err)}",
                    original_exception=err
                ) from err
        return self._client

    def get_database(self) -> Database:
        """Returns the Pharmavigil MongoDB database instance."""
        client = self.get_client()
        return client[self.db_name]

    def get_adverse_reports_collection(self) -> Collection:
        """Returns the adverse_reports polymorphic collection."""
        db = self.get_database()
        return db[self.adverse_collection_name]

    def ping(self) -> bool:
        """Checks if MongoDB server is reachable."""
        try:
            client = self.get_client()
            client.admin.command('ping')
            return True
        except Exception:
            return False

    def close(self):
        """Closes the MongoDB connection pool."""
        if self._client:
            self._client.close()
            self._client = None


# Singleton MongoDB client instance
mongo_client = MongoDBClient()
