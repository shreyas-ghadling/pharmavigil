import uuid
from datetime import datetime, timedelta, timezone
from app.database.mongo_client import mongo_client
from app.services.mongo_service import mongo_service


def test_identity_windows_and_review_reopening():
    collection = mongo_client.get_adverse_reports_collection()
    medicine_id = 990001
    now = datetime.now(timezone.utc)
    def insert(name, days):
        collection.insert_one({"report_id": uuid.uuid4().hex, "medicine_id": medicine_id, "medicine_name": name,
                               "severity_score": 3, "reported_at": (now - timedelta(days=days)).isoformat(),
                               "symptoms": [{"name": "Nausea", "is_critical": False}]})
    insert("Old name", 2)
    insert("New name", 3)
    insert("Old name", 40)
    row = next(r for r in mongo_service.execute_safety_signal_detection_pipeline(1, 1, 30) if r.get("medicine_id") == medicine_id)
    assert row["incident_count"] == 2 and row["previous_period_count"] == 1
    user = {"user_id": 1, "username": "officer", "full_name": "Officer"}
    mongo_service.review_pattern(row["medicine_key"], row["symptom"], 30, row["revision"], "CLOSED", "Assessment recorded", user)
    row = next(r for r in mongo_service.execute_safety_signal_detection_pipeline(1, 1, 30) if r.get("medicine_id") == medicine_id)
    assert row["review_status"] == "CLOSED"
    insert("Another name", 1)
    row = next(r for r in mongo_service.execute_safety_signal_detection_pipeline(1, 1, 30) if r.get("medicine_id") == medicine_id)
    assert row["review_status"] == "NEEDS_REVIEW"
    collection.insert_one({"report_id": uuid.uuid4().hex, "medicine_id": 990002, "medicine_name": "Old name",
                           "severity_score": 3, "symptoms": [{"name": "Nausea"}]})
    rows = [r for r in mongo_service.execute_safety_signal_detection_pipeline(1, 1) if r.get("medicine_id") in {990001, 990002}]
    assert len(rows) == 2
