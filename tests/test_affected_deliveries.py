from app.services.sql_service import sql_service


def test_expired_deliveries_are_included_without_recall():
    rows = sql_service.get_high_risk_quarantine_trace()
    expired = [r for r in rows if r["batch_number"] == "BCH-GLU-5502"]
    assert expired
    assert all(r["affected_reason"] == "EXPIRED" for r in expired)
    assert sum(r["historically_distributed_units"] for r in expired) == 10000
    assert all(r["stock_unit"] == "tablet" for r in expired)
