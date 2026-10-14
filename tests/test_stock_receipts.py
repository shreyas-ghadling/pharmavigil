import uuid
from datetime import date, timedelta
import pytest
from app.services.sql_service import sql_service


def test_registration_receipts_and_dispatch_are_separate():
    batch = "BCH-RECEIPT-" + uuid.uuid4().hex[:8].upper()
    today = date.today()
    sql_service.insert_batch(batch, 101, str(today), str(today + timedelta(days=365)), 100)
    def balance():
        return next(r["current_stock"] for r in sql_service.get_inventory_stock_overview() if r["batch_number"] == batch)
    assert balance() == 0
    with pytest.raises(ValueError): sql_service.dispatch_batch_to_hospital(batch, 1, 1)
    sql_service.receive_stock(batch, 30, str(today), "SHIPMENT-A", "tester")
    sql_service.receive_stock(batch, 30, str(today), "SHIPMENT-A", "tester")
    sql_service.receive_stock(batch, 20, str(today), "SHIPMENT-B", "tester")
    assert balance() == 50
    sql_service.dispatch_batch_to_hospital(batch, 1, 10)
    assert balance() == 40
    with pytest.raises(ValueError): sql_service.receive_stock(batch, 60, str(today), "SHIPMENT-C", "tester")


def test_rerunning_migration_does_not_create_stock_for_new_registration():
    from scripts.migrate_workflows import migrate_stock
    from app.database.mysql_client import mysql_client
    batch = "BCH-EMPTY-" + uuid.uuid4().hex[:8].upper()
    today = date.today()
    sql_service.insert_batch(batch, 101, str(today), str(today + timedelta(days=365)), 100)
    migrate_stock(mysql_client)
    migrate_stock(mysql_client)
    assert next(r["current_stock"] for r in sql_service.get_inventory_stock_overview() if r["batch_number"] == batch) == 0


def test_dispatch_dates_respect_receipts_manufacture_and_today():
    batch = "BCH-DATES-" + uuid.uuid4().hex[:8].upper()
    today = date.today()
    sql_service.insert_batch(batch, 101, str(today - timedelta(days=10)), str(today + timedelta(days=365)), 100)
    sql_service.receive_stock(batch, 100, str(today), "SHIPMENT-A", "tester")
    for day in [today + timedelta(days=1), today - timedelta(days=11), today - timedelta(days=1)]:
        with pytest.raises(ValueError): sql_service.dispatch_batch_to_hospital(batch, 1, 1, str(day))
    sql_service.dispatch_batch_to_hospital(batch, 1, 1, str(today))


def test_future_manufactured_batch_is_not_dispatch_eligible():
    batch = "BCH-FUTURE-" + uuid.uuid4().hex[:8].upper()
    today = date.today()
    sql_service.insert_batch(batch, 101, str(today + timedelta(days=1)), str(today + timedelta(days=365)), 100)
    assert batch not in {r["batch_number"] for r in sql_service.get_batches(101, only_active=True)}
    with pytest.raises(ValueError): sql_service.dispatch_batch_to_hospital(batch, 1, 1)
