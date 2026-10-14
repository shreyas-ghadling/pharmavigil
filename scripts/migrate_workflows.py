"""Apply additive workflow migrations without resetting application data."""
import argparse
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import dotenv_values
from app.database.mysql_client import MySQLClient
from app.database.mongo_client import MongoDBClient


def clients(hosted=False, database="pharmavigil_db"):
    sql, mongo = MySQLClient(), MongoDBClient()
    if hosted:
        env = dotenv_values(ROOT / ".env.production.local")
        sql.host, sql.port = env["MYSQL_HOST"], int(env["MYSQL_PORT"])
        sql.user, sql.password, sql.database = env["MYSQL_USER"], env["MYSQL_PASSWORD"], env["MYSQL_DATABASE"]
        mongo.uri, mongo.db_name = env["MONGO_URI"], env["MONGO_DB_NAME"]
    else:
        sql.database = mongo.db_name = database
    return sql, mongo


def migrate_mongo(mongo):
    collection = mongo.get_adverse_reports_collection()
    collection.create_index("submission_key", unique=True, sparse=True, name="idx_submission_key_unique")
    collection.create_index("case_key", unique=True, sparse=True, name="idx_case_key_unique")
    print("Report retry and case-reference indexes ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hosted", action="store_true")
    parser.add_argument("--database", default="pharmavigil_db")
    args = parser.parse_args()
    sql, mongo = clients(args.hosted, args.database)
    migrate_mongo(mongo)
    mongo.close()
