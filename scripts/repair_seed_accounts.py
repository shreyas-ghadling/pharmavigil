"""One-time migration: replace only known seed placeholders, retaining passwords."""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import dotenv_values
from app.database.mysql_client import MySQLClient
from app.utils.auth import verify_password

parser = argparse.ArgumentParser()
parser.add_argument("--hosted", action="store_true")
parser.add_argument("--database", default="pharmavigil_test")
args = parser.parse_args()
client = MySQLClient()
if args.hosted:
    env = dotenv_values(ROOT / ".env.production.local")
    client.host = env["MYSQL_HOST"]
    client.port = int(env["MYSQL_PORT"])
    client.user = env["MYSQL_USER"]
    client.password = env["MYSQL_PASSWORD"]
    client.database = env["MYSQL_DATABASE"]
else:
    client.database = args.database

original = subprocess.check_output(["git", "show", "6578e2b:sql_scripts/seed_data.sql"], cwd=ROOT, text=True)
updated = (ROOT / "sql_scripts/seed_data.sql").read_text()
for username, password in [("doctor_smith", "doctor123"), ("pharmacist_jane", "pharmacist123"), ("admin_officer", "admin123")]:
    pattern = r"'" + username + r"',\s*'([^']+)'"
    old_hash = re.search(pattern, original)[1]
    new_hash = re.search(pattern, updated)[1]
    row = client.execute_one("SELECT password_hash FROM users WHERE username = %s", (username,))
    if not row:
        print(username, "not present; left unchanged")
        continue
    if verify_password(password, row["password_hash"]):
        print(username, "already verifies")
        continue
    if row["password_hash"] != old_hash:
        print(username, "custom hash; left unchanged")
        continue
    client.execute_update("UPDATE users SET password_hash = %s WHERE username = %s AND password_hash = %s", (new_hash, username, old_hash))
    print(username, "known placeholder repaired")
