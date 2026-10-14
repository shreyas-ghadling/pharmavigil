"""
MongoDB Business Logic Service for Pharmavigil
Executes adverse reaction document ingestion, 6-stage Signal Detection Aggregation Pipeline,
and full-text search across clinical observations.
"""

from typing import List, Dict, Any, Optional
from app.database.mongo_client import mongo_client
from app.models.schemas import AdverseReportCreate
from app.models.medicine import SafetyAuditor
from app.utils.exceptions import DatabaseConnectionError


class MongoService:
    """Encapsulates document operations and aggregation pipelines."""

    def insert_adverse_report(self, report_payload: Dict[str, Any]) -> str:
        """
        Validates input payload via Pydantic AdverseReportCreate and persists into MongoDB.
        Returns the unique tracking report_id.
        """
        # 1. Pydantic Boundary Validation
        validated = AdverseReportCreate(**report_payload)
        doc = validated.model_dump()

        # 2. Verify medicine, and a batch when supplied. Unknown batches remain null.
        from app.services.sql_service import sql_service
        from app.utils.exceptions import BatchMedicineMismatchError, DatabaseConnectionError

        try:
            if doc["batch_number"] is None:
                medicines = sql_service.get_all_medicines()
                batch_info = None
            else:
                batch_info = sql_service.get_batch_by_number(doc["batch_number"])
        except Exception as err:
            raise DatabaseConnectionError(
                f"Relational verification failed: MySQL database is unreachable. Cannot verify batch '{doc['batch_number']}'.",
                original_exception=err
            ) from err

        if doc["batch_number"] is None:
            medicine = next((m for m in medicines if m["medicine_id"] == doc["medicine_id"]), None)
            if not medicine:
                raise ValueError("Choose a registered medicine.")
            doc["medicine_name"] = medicine["commercial_name"]
        elif not batch_info:
            raise BatchMedicineMismatchError(
                batch_number=doc["batch_number"],
                medicine_id=doc["medicine_id"],
                message=f"Validation Error: Batch '{doc['batch_number']}' does not exist in the database."
            )

        if batch_info and batch_info["medicine_id"] != doc["medicine_id"]:
            raise BatchMedicineMismatchError(
                batch_number=doc["batch_number"],
                medicine_id=doc["medicine_id"],
                expected_medicine_id=batch_info["medicine_id"],
                message=(
                    f"Validation Error: Batch '{doc['batch_number']}' belongs to medicine ID "
                    f"{batch_info['medicine_id']} ({batch_info['commercial_name']}), "
                    f"not selected medicine ID {doc['medicine_id']} ({doc['medicine_name']})."
                )
            )

        # 3. Insert into MongoDB
        collection = mongo_client.get_adverse_reports_collection()
        import hashlib, json
        from pymongo.errors import DuplicateKeyError
        from app.utils.exceptions import PharmavigilException
        for key in ("submission_key", "case_key"):
            if doc.get(key) is None:
                doc.pop(key, None)
        doc["submission_fingerprint"] = hashlib.sha256(json.dumps(
            {k: v for k, v in doc.items() if k not in {"report_id", "reported_at", "submission_key", "case_key"}},
            sort_keys=True, default=str).encode()).hexdigest()
        try:
            collection.insert_one(doc)
        except DuplicateKeyError:
            if doc.get("submission_key"):
                existing = collection.find_one({"submission_key": doc["submission_key"]})
                if existing and existing.get("submission_fingerprint") == doc["submission_fingerprint"]:
                    return existing["report_id"]
            if doc.get("case_key") and collection.find_one({"case_key": doc["case_key"]}):
                raise PharmavigilException("This case reference is already recorded for your account. Use a distinct reference for a different case.")
            raise PharmavigilException("This submission key is already used. Start a new report for a different case.")
        return doc["report_id"]

    def get_adverse_reports(self, filter_dict: Optional[Dict[str, Any]] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves raw adverse event documents."""
        collection = mongo_client.get_adverse_reports_collection()
        cursor = collection.find(filter_dict or {}, {"_id": 0}).sort("reported_at", -1).limit(limit)
        return list(cursor)

    def get_case_review_queue(self, page: int = 1, page_size: int = 25) -> Dict[str, Any]:
        collection = mongo_client.get_adverse_reports_collection()
        query = {"$and": [
            {"review.status": {"$ne": "REVIEWED"}},
            {"$or": [{"seriousness_criteria.0": {"$exists": True}},
                     {"seriousness_criteria": None, "symptoms.is_critical": True}]},
        ]}
        return {"items": list(collection.find(query, {"_id": 0}).sort("reported_at", -1)
                              .skip((page - 1) * page_size).limit(page_size)),
                "total": collection.count_documents(query)}

    def review_case(self, report_id: str, status: str, notes: str, user: Dict[str, Any]):
        from datetime import datetime, timezone
        review = {"status": status, "notes": notes, "reviewed_at": datetime.now(timezone.utc).isoformat(),
                  "reviewed_by": {k: user[k] for k in ("user_id", "username", "full_name")}}
        result = mongo_client.get_adverse_reports_collection().update_one(
            {"report_id": report_id}, {"$set": {"review": review}, "$push": {"review_history": review}})
        if not result.matched_count:
            raise ValueError("The selected report does not exist.")
        return review

    def execute_safety_signal_detection_pipeline(self, min_severity: float = 3, min_incidents: int = 2) -> List[Dict[str, Any]]:
        """
        Summarizes symptom entries across all available reports for review.
        Filters completed groups and retains legacy field names for API compatibility.
        """
        pipeline = [
            # Include all intensity levels when calculating counts and averages.
            {
                "$unwind": "$symptoms"
            },
            {"$group": {"_id": {"report": "$_id", "medicine": "$medicine_name",
                                     "symptom": {"$toLower": {"$trim": {"input": "$symptoms.name"}}}},
                         "medicine_name": {"$first": "$medicine_name"},
                         "symptom_name": {"$first": "$symptoms.name"},
                         "severity_score": {"$first": "$severity_score"},
                         "seriousness_criteria": {"$first": "$seriousness_criteria"},
                         "legacy_flag": {"$max": "$symptoms.is_critical"}}},
            # Stage 3: Group by drug and symptom to compute frequencies
            {
                "$group": {
                    "_id": {
                        "medicine_name": "$medicine_name",
                        "symptom": "$_id.symptom"
                    },
                    "incident_count": {"$sum": 1},
                    "avg_severity": {"$avg": "$severity_score"},
                    "reported_serious_cases": {"$sum": {"$cond": [
                        {"$gt": [{"$size": {"$ifNull": ["$seriousness_criteria", []]}}, 0]}, 1, 0
                    ]}},
                    "seriousness_unknown_entries": {"$sum": {"$cond": [
                        {"$eq": [{"$ifNull": ["$seriousness_criteria", None]}, None]}, 1, 0
                    ]}},
                    "critical_cases": {
                        "$sum": {
                            "$cond": ["$legacy_flag", 1, 0]
                        }
                    }
                }
            },
            # Filter completed groups using the requested review thresholds.
            {
                "$match": {
                    "incident_count": {"$gte": min_incidents},
                    "avg_severity": {"$gte": min_severity},
                }
            },
            # Stage 5: Format output projection and compute signal risk score
            {
                "$project": {
                    "_id": 0,
                    "medicine": "$_id.medicine_name",
                    "symptom": "$_id.symptom",
                    "incident_count": 1,
                    "avg_severity": {"$round": ["$avg_severity", 2]},
                    "critical_cases": 1,
                    "reported_serious_cases": 1,
                    "seriousness_unknown_entries": 1,
                    "signal_risk_score": {
                        "$round": [
                            {"$multiply": ["$incident_count", "$avg_severity"]},
                            2
                        ]
                    }
                }
            },
            # Rank scores; classification is applied by the shared domain rule.
            {
                "$sort": {"signal_risk_score": -1}
            }
        ]

        collection = mongo_client.get_adverse_reports_collection()
        results = list(collection.aggregate(pipeline))

        # Enrich results with SafetyAuditor recommendations
        for row in results:
            eval_data = SafetyAuditor.evaluate_signal_alert(
                medicine_name=row["medicine"],
                symptom=row["symptom"],
                incident_count=row["incident_count"],
                avg_severity=row["avg_severity"],
                critical_cases=row["critical_cases"],
                priority_score=row["signal_risk_score"],
            )
            row["alert_level"] = eval_data["alert_level"]
            row["risk_level"] = eval_data["alert_level"]
            row["priority_score"] = eval_data["priority_score"]
            row["review_priority"] = eval_data["review_priority"]
            row["recommendation"] = eval_data["recommendation"]

        return results

    def search_clinical_notes_text(self, search_query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Executes Section 6.4 MongoDB Text Search Index:
        Retrieves doctor free-text notes matching search terms without NLP library overhead.
        Falls back cleanly to case-insensitive regex if text index is rebuilding.
        """
        if not search_query or not search_query.strip():
            return self.get_adverse_reports(limit=limit)

        collection = mongo_client.get_adverse_reports_collection()
        try:
            # 1. Native Full-Text Search with textScore relevance ranking
            cursor = collection.find(
                {"$text": {"$search": search_query.strip()}},
                {"score": {"$meta": "textScore"}, "_id": 0}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            return list(cursor)
        except Exception:
            # 2. Fallback regex query
            regex_query = {"clinical_notes": {"$regex": search_query.strip(), "$options": "i"}}
            cursor = collection.find(regex_query, {"_id": 0}).limit(limit)
            return list(cursor)

    def get_symptom_frequency_distribution(self) -> List[Dict[str, Any]]:
        """Aggregates most frequent symptoms across the entire system."""
        pipeline = [
            {"$unwind": "$symptoms"},
            {
                "$group": {
                    "_id": "$symptoms.name",
                    "total_count": {"$sum": 1},
                    "critical_count": {
                        "$sum": {"$cond": ["$symptoms.is_critical", 1, 0]}
                    }
                }
            },
            {"$sort": {"total_count": -1}},
            {"$limit": 10}
        ]
        collection = mongo_client.get_adverse_reports_collection()
        return list(collection.aggregate(pipeline))


# Singleton Mongo service instance
mongo_service = MongoService()
