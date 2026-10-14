import uuid
from app.database.mongo_client import mongo_client
from app.services.mongo_service import mongo_service


def test_single_low_intensity_serious_case_is_reviewable():
    report_id = uuid.uuid4().hex
    collection = mongo_client.get_adverse_reports_collection()
    collection.insert_one({"report_id": report_id, "medicine_name": "Single case", "severity_score": 1,
                           "seriousness_criteria": ["HOSPITALIZATION"], "symptoms": [{"name": "Nausea"}]})
    assert report_id in {row["report_id"] for row in mongo_service.get_case_review_queue()["items"]}
    user = {"user_id": 1, "username": "officer", "full_name": "Officer"}
    mongo_service.review_case(report_id, "FOLLOW_UP", "Need outcome details", user)
    assert report_id in {row["report_id"] for row in mongo_service.get_case_review_queue()["items"]}
    mongo_service.review_case(report_id, "REVIEWED", "Case assessment recorded", user)
    assert report_id not in {row["report_id"] for row in mongo_service.get_case_review_queue()["items"]}
    assert len(collection.find_one({"report_id": report_id})["review_history"]) == 2
