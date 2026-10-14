"""Reporting eligibility is independent of dispensing eligibility."""
from datetime import date, timedelta
import uuid

import pytest
from app.database.mongo_client import mongo_client
from app.services.mongo_service import mongo_service
from app.services.sql_service import sql_service
from app.utils.exceptions import ExpiredBatchDispenseError, RecalledBatchOperationError


@pytest.mark.parametrize("status", ["EXPIRED", "RECALLED", "UNDER_INVESTIGATION"])
def test_flagged_batch_can_be_reported_but_not_dispatched(status):
    today = date.today()
    batch = "BCH-REPORT-" + uuid.uuid4().hex[:8].upper()
    expiry = today - timedelta(days=1) if status == "EXPIRED" else today + timedelta(days=365)
    sql_service.insert_batch(batch, 101, str(today - timedelta(days=365)), str(expiry), 100, status)
    assert batch in {row["batch_number"] for row in sql_service.get_batches(101)}
    assert batch not in {row["batch_number"] for row in sql_service.get_batches(101, only_active=True)}
    report_id = mongo_service.insert_adverse_report({
        "medicine_id": 101, "medicine_name": "Cardiomax", "batch_number": batch,
        "patient_demographics": {"age": 40, "gender": "Female"},
        "symptoms": [{"name": "Nausea", "onset_minutes": 60}], "severity_score": 2,
    })
    saved = mongo_client.get_adverse_reports_collection().find_one({"report_id": report_id})
    assert saved["batch_number"] == batch
    with pytest.raises((ExpiredBatchDispenseError, RecalledBatchOperationError)):
        sql_service.dispatch_batch_to_hospital(batch, 1, 1)
