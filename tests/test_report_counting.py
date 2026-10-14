import uuid
import pytest
from app.models.schemas import AdverseReportCreate
from app.services.mongo_service import mongo_service
from app.database.mongo_client import mongo_client


def payload():
    return {"medicine_id": 101, "medicine_name": "Cardiomax", "batch_number": None, "reporter_type": "PATIENT",
            "patient_demographics": {"age": 35, "gender": "Male"}, "severity_score": 2,
            "symptoms": [{"name": "Nausea", "onset_minutes": None}]}


def test_retries_return_original_report_without_merging_different_cases():
    data = {**payload(), "submission_key": uuid.uuid4().hex}
    assert mongo_service.insert_adverse_report(data) == mongo_service.insert_adverse_report(data)
    assert mongo_service.insert_adverse_report(payload()) != mongo_service.insert_adverse_report(payload())


def test_duplicate_symptoms_rejected_and_legacy_duplicates_count_once():
    data = payload()
    data["symptoms"] *= 2
    with pytest.raises(ValueError):
        AdverseReportCreate(**data)
    name = uuid.uuid4().hex
    mongo_client.get_adverse_reports_collection().insert_one({"report_id": uuid.uuid4().hex, "medicine_name": name,
        "severity_score": 3, "symptoms": [{"name": "Nausea"}, {"name": "nausea"}]})
    row = next(r for r in mongo_service.execute_safety_signal_detection_pipeline(1, 1) if r["medicine"] == name)
    assert row["incident_count"] == 1
