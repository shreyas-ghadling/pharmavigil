"""
MongoDB Setup Script for Pharmavigil
Initializes collections and creates specialized indexes (Text search, batch lookups, compound safety keys).
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from app.database.mongo_client import mongo_client
import pymongo


def setup_mongo_indexes():
    """Configures indexes on the adverse_reports collection."""
    print("Connecting to MongoDB to configure collections and indexes...")
    collection = mongo_client.get_adverse_reports_collection()
    
    # 1. Text Index on clinical_notes for native keyword retrieval
    print("Creating text index on 'clinical_notes'...")
    collection.create_index([("clinical_notes", pymongo.TEXT)], name="idx_clinical_notes_text")
    
    # 2. Index on batch_number for instant batch traceability
    print("Creating index on 'batch_number'...")
    collection.create_index([("batch_number", pymongo.ASCENDING)], name="idx_batch_number")
    
    # 3. Compound index on medicine_name and severity_score for risk filtering
    print("Creating compound index on (medicine_name, severity_score)...")
    collection.create_index(
        [("medicine_name", pymongo.ASCENDING), ("severity_score", pymongo.DESCENDING)],
        name="idx_medicine_severity"
    )
    
    # 4. Index on report_id for uniqueness
    print("Creating unique index on 'report_id'...")
    collection.create_index([("report_id", pymongo.ASCENDING)], unique=True, name="idx_report_id_unique")

    print("MongoDB indexes successfully created.")


if __name__ == "__main__":
    try:
        setup_mongo_indexes()
    except Exception as e:
        print(f"Error configuring MongoDB indexes: {e}")
        sys.exit(1)
