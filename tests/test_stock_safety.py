"""Concurrent dispatch safety, using the isolated integration database."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import uuid
from app.services.sql_service import sql_service
from app.database.mysql_client import mysql_client

def test_concurrent_dispatch_cannot_exceed_available_stock():
    batch = "BCH-STOCK-" + uuid.uuid4().hex[:8].upper()
    today = date.today()
    sql_service.insert_batch(batch, 101, today.isoformat(), (today + timedelta(days=365)).isoformat(), 100)
    def attempt():
        try:
            sql_service.dispatch_batch_to_hospital(batch, 1, 60)
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: attempt(), range(2)))
    assert outcomes.count(True) == 1
    row = mysql_client.execute_one("SELECT SUM(quantity_delivered) AS total FROM batch_distribution WHERE batch_number = %s", (batch,))
    assert row["total"] == 60
