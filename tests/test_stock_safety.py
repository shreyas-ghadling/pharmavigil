"""Concurrent dispatch safety, using the isolated integration database."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import uuid
from app.services.sql_service import sql_service
from app.database.mysql_client import mysql_client
from app.utils.exceptions import RecalledBatchOperationError

def test_concurrent_dispatch_cannot_exceed_available_stock():
    batch = "BCH-STOCK-" + uuid.uuid4().hex[:8].upper()
    today = date.today()
    sql_service.insert_batch(batch, 101, today.isoformat(), (today + timedelta(days=365)).isoformat(), 100)
    sql_service.receive_stock(batch, 100, today.isoformat(), "TEST-RECEIPT", "tester")
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


def test_concurrent_recalls_create_one_audit():
    batch = 'BCH-RECALL-' + uuid.uuid4().hex[:8].upper()
    today = date.today()
    sql_service.insert_batch(batch, 101, today.isoformat(), (today + timedelta(days=365)).isoformat(), 100)
    def attempt():
        try:
            sql_service.execute_emergency_recall(batch, 'Concurrent safety review', 'tester')
            return True
        except RecalledBatchOperationError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: attempt(), range(2)))
    assert outcomes.count(True) == 1
    row = mysql_client.execute_one('SELECT COUNT(*) AS n FROM recall_audit WHERE batch_number=%s', (batch,))
    assert row['n'] == 1


def test_recall_and_dispatch_are_serialized():
    batch = 'BCH-RACE-' + uuid.uuid4().hex[:8].upper()
    today = date.today()
    sql_service.insert_batch(batch, 101, today.isoformat(), (today + timedelta(days=365)).isoformat(), 100)
    sql_service.receive_stock(batch, 100, today.isoformat(), 'RACE-RECEIPT', 'tester')
    def dispatch():
        try:
            sql_service.dispatch_batch_to_hospital(batch, 1, 30)
            return 30
        except RecalledBatchOperationError:
            return 0
    with ThreadPoolExecutor(max_workers=2) as pool:
        dispatched = pool.submit(dispatch)
        recalled = pool.submit(sql_service.execute_emergency_recall, batch, 'Dispatch race safety concern', 'tester')
        quantity, recall = dispatched.result(), recalled.result()
    assert recall['distributed_quantity_at_initiation'] == quantity
    with __import__('pytest').raises(RecalledBatchOperationError):
        sql_service.dispatch_batch_to_hospital(batch, 1, 1)
