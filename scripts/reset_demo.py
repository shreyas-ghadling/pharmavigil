"""
Pharmavigil Demo Reset Script
Reloads the MySQL relational schema, stored procedures, and seed data,
clears recall_audit, and reseeds MongoDB to exactly 22 clinical reports.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import config
from app.database.mongo_client import mongo_client
from app.database.mysql_client import mysql_client
from app.database.setup_mongo import setup_mongo_indexes
from app.database.seed_mongo import seed_mongodb


def reset_demo():
    print("=" * 65)
    print("   PHARMAVIGIL DEMO DATABASE RESET")
    print("=" * 65)

    # 1. Reset MySQL
    print("\n[1/3] Reloading MySQL Schema, Stored Procedures, and Seed Data...")
    
    # Locate mysql CLI
    candidate_paths = [
        Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"),
        Path(r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"),
    ]
    mysql_bin = None
    for p in candidate_paths:
        if p.exists():
            mysql_bin = str(p)
            break
    if not mysql_bin:
        mysql_bin = "mysql"

    env = os.environ.copy()
    env["MYSQL_PWD"] = config.mysql.password

    sql_files = ["schema.sql", "stored_procedures.sql", "seed_data.sql"]
    for s_name in sql_files:
        s_path = BASE_DIR / "sql_scripts" / s_name
        if not s_path.exists():
            raise FileNotFoundError(f"Missing SQL script: {s_path}")
        
        cmd = [
            mysql_bin,
            "-h", config.mysql.host,
            "-P", str(config.mysql.port),
            "-u", config.mysql.user,
            "-e", f"source {s_path.resolve().as_posix()}"
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error executing {s_name}: {res.stderr}")
            sys.exit(res.returncode)
        print(f"  [OK] Executed {s_name}")

    # Ensure recall_audit is completely cleared and auto-increment reset
    print("\n[2/3] Resetting MySQL recall_audit table...")
    mysql_client.execute_update("DELETE FROM recall_audit;")
    mysql_client.execute_update("ALTER TABLE recall_audit AUTO_INCREMENT = 1;")
    print("  [OK] recall_audit emptied (AUTO_INCREMENT reset)")

    # 2. Reset MongoDB
    print("\n[3/3] Reseeding MongoDB telemetry...")
    setup_mongo_indexes()
    seed_mongodb()

    # 3. Verification
    print("\n" + "=" * 65)
    print("   VERIFYING DEMO PRISTINE STATE")
    print("=" * 65)

    coll = mongo_client.get_adverse_reports_collection()
    mongo_count = coll.count_documents({})
    print(f"  - MongoDB Adverse Reports : {mongo_count} (Expected: 22)")
    assert mongo_count == 22, f"Expected 22 MongoDB reports, got {mongo_count}"

    b_res = mysql_client.execute_one("SELECT COUNT(*) AS cnt FROM batches;")
    batch_count = b_res["cnt"]
    print(f"  - MySQL Registered Batches: {batch_count} (Expected: 10)")
    assert batch_count == 10, f"Expected 10 MySQL batches, got {batch_count}"

    a_res = mysql_client.execute_one("SELECT COUNT(*) AS cnt FROM recall_audit;")
    audit_count = a_res["cnt"]
    print(f"  - MySQL Recall Audit Rows : {audit_count} (Expected: 0)")
    assert audit_count == 0, f"Expected 0 recall audits, got {audit_count}"

    print("\n>>> DEMO RESET COMPLETE: Both databases are in a pristine presentation state! <<<\n")


if __name__ == "__main__":
    reset_demo()
