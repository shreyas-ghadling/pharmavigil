from datetime import date, timedelta
from uuid import uuid4
from app.services.sql_service import sql_service


def test_central_only_recall_is_visible_with_actual_ledger_balance():
    batch = 'BCH-CENTRAL-' + uuid4().hex[:8].upper()
    today = date.today()
    sql_service.insert_batch(batch, 101, today.isoformat(), (today + timedelta(days=365)).isoformat(), 100)
    sql_service.receive_stock(batch, 40, today.isoformat(), 'RECEIPT-1', 'tester')
    sql_service.execute_emergency_recall(batch, 'Central stock safety concern', 'tester')
    row = next(r for r in sql_service.get_affected_central_stock() if r['batch_number'] == batch)
    assert row['current_stock'] == 40
    assert row['affected_reason'] == 'RECALLED'
    assert not any(r['batch_number'] == batch for r in sql_service.get_high_risk_quarantine_trace())
