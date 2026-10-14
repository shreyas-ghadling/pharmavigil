"""Group filtering must preserve the underlying report population."""
import uuid
from app.database.mongo_client import mongo_client
from app.services.mongo_service import mongo_service


def test_average_filter_preserves_low_intensity_reports():
    medicine = "Filter-check-" + uuid.uuid4().hex
    collection = mongo_client.get_adverse_reports_collection()
    collection.insert_many([
        {"report_id": uuid.uuid4().hex, "medicine_name": medicine, "severity_score": intensity,
         "seriousness_criteria": ["HOSPITALIZATION"] if intensity == 5 else None,
         "symptoms": [{"name": "Nausea", "is_critical": False}]}
        for intensity in [1, 5]
    ])
    def matching(threshold):
        return [row for row in mongo_service.execute_safety_signal_detection_pipeline(threshold, 2)
                if row["medicine"] == medicine]
    baseline = matching(1)[0]
    filtered = matching(3)[0]
    assert baseline["incident_count"] == filtered["incident_count"] == 2
    assert baseline["avg_severity"] == filtered["avg_severity"] == 3
    assert filtered["priority_score"] == 6
    assert filtered["reported_serious_cases"] == 1
    assert filtered["risk_level"] == filtered["alert_level"] == "HIGH"
    assert matching(3.5) == []


def test_legacy_flags_remain_separate_from_serious_outcomes():
    medicine = "Legacy-check-" + uuid.uuid4().hex
    collection = mongo_client.get_adverse_reports_collection()
    collection.insert_one({"report_id": uuid.uuid4().hex, "medicine_name": medicine,
                           "severity_score": 5, "symptoms": [{"name": "Nausea", "is_critical": True}]})
    row = next(row for row in mongo_service.execute_safety_signal_detection_pipeline(1, 1) if row["medicine"] == medicine)
    assert row["critical_cases"] == 1
    assert row["reported_serious_cases"] == 0
