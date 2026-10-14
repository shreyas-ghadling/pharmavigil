"""Correct known demo catalog entries without resetting inventory or user reports."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import dotenv_values
from app.database.mysql_client import MySQLClient
from app.database.mongo_client import MongoDBClient


def repair_strength(sql, mongo):
    changed = sql.execute_update(
        "UPDATE medicines SET strength = %s WHERE medicine_id = %s "
        "AND commercial_name = %s AND generic_name = %s AND strength = %s",
        ("5 mg", 101, "Cardiomax", "Amlodipine Besylate", "50mg"),
    )
    # Only the exact seeded narrative is corrected. User-entered notes are retained.
    result = mongo.get_adverse_reports_collection().update_one(
        {"report_id": "ADR-2026-0003", "medicine_id": 101,
         "clinical_notes": "Self-reported feeling extreme lightheadedness and acute dizziness after taking Cardiomax 50mg."},
        {"$set": {"clinical_notes": "Self-reported feeling extreme lightheadedness and acute dizziness after taking Cardiomax 5 mg."}},
    )
    print(f"Catalog entries corrected: {changed}; seeded narratives corrected: {result.modified_count}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hosted", action="store_true")
    parser.add_argument("--database", default="pharmavigil_db")
    args = parser.parse_args()
    sql, mongo = MySQLClient(), MongoDBClient()
    if args.hosted:
        env = dotenv_values(ROOT / ".env.production.local")
        sql.host, sql.port = env["MYSQL_HOST"], int(env["MYSQL_PORT"])
        sql.user, sql.password, sql.database = env["MYSQL_USER"], env["MYSQL_PASSWORD"], env["MYSQL_DATABASE"]
        mongo.uri, mongo.db_name = env["MONGO_URI"], env["MONGO_DB_NAME"]
    else:
        sql.database = mongo.db_name = args.database
    repair_strength(sql, mongo)
    mongo.close()
