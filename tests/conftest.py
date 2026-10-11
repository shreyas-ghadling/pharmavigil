"""
Pytest Configuration & Fixtures for Pharmavigil
Enforces complete database isolation: tests run against 'pharmavigil_test'
and never touch the production/demo database 'pharmavigil_db'.
"""

import os
import subprocess
import tempfile
from pathlib import Path
import pytest

from app.config import config
from app.database.mysql_client import mysql_client
from app.database.mongo_client import mongo_client
from app.database.setup_mongo import setup_mongo_indexes
from app.database.seed_mongo import seed_mongodb

BASE_DIR = Path(__file__).resolve().parent.parent


def initialize_test_mysql():
    """Initializes schema, stored procedures, and seed data in MySQL pharmavigil_test."""
    # 1. Ensure test database exists
    conn = mysql_client.get_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS pharmavigil_test;")
    conn.commit()
    cursor.close()
    conn.close()

    # 2. Point mysql_client to test database
    mysql_client.database = "pharmavigil_test"

    # 3. Locate mysql CLI
    candidate_paths = [
        Path(r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"),
        Path(r"C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe"),
    ]
    mysql_bin = "mysql"
    for p in candidate_paths:
        if p.exists():
            mysql_bin = str(p)
            break

    env = os.environ.copy()
    env["MYSQL_PWD"] = config.mysql.password

    # Execute scripts with pharmavigil_test
    for s_name in ["schema.sql", "stored_procedures.sql", "seed_data.sql"]:
        raw_sql = (BASE_DIR / "sql_scripts" / s_name).read_text(encoding="utf-8")
        test_sql = raw_sql.replace("pharmavigil_db", "pharmavigil_test")
        with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as tf:
            tf.write(test_sql)
            tmp_path = tf.name

        cmd = [
            mysql_bin,
            "-h", config.mysql.host,
            "-P", str(config.mysql.port),
            "-u", config.mysql.user,
            "-e", f"source {Path(tmp_path).as_posix()}"
        ]
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        if res.returncode != 0:
            raise RuntimeError(f"Failed to load {s_name} into pharmavigil_test: {res.stderr}")

    # Ensure recall_audit is pristine in test database
    mysql_client.execute_update("DELETE FROM recall_audit;")
    mysql_client.execute_update("ALTER TABLE recall_audit AUTO_INCREMENT = 1;")


def initialize_test_mongodb():
    """Configures collections, indexes, and seeds test data in MongoDB pharmavigil_test."""
    mongo_client.db_name = "pharmavigil_test"
    setup_mongo_indexes()
    seed_mongodb()


@pytest.fixture(scope="session", autouse=True)
def setup_test_databases():
    """
    Session-level autouse fixture:
    Switches both MySQL and MongoDB client connections to pharmavigil_test
    and initializes pristine schemas and seed data.
    """
    orig_mysql_db = mysql_client.database
    orig_mongo_db = mongo_client.db_name

    try:
        initialize_test_mysql()
    except Exception as e:
        print(f"Warning: Could not initialize MySQL test database: {e}")

    try:
        initialize_test_mongodb()
    except Exception as e:
        print(f"Warning: Could not initialize MongoDB test database: {e}")

    yield

    # Restore original database settings
    mysql_client.database = orig_mysql_db
    mongo_client.db_name = orig_mongo_db
