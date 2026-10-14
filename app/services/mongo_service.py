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

    def execute_safety_signal_detection_pipeline(self, min_severity: float = 3, min_incidents: int = 2, window_days: int = 0) -> List[Dict[str, Any]]:
        """
        Summarizes symptom entries across all available reports for review.
        Filters completed groups and retains legacy field names for API compatibility.
        """
        pipeline = [
            # Include all intensity levels when calculating counts and averages.
            {
                "$unwind": "$symptoms"
            },
            {"$group": {"_id": {"report": "$_id", "medicine": {"$ifNull": ["$medicine_id", {"$concat": ["legacy:", "$medicine_name"]}]},
                                     "symptom": {"$toLower": {"$trim": {"input": "$symptoms.name"}}}},
                         "medicine_name": {"$first": "$medicine_name"},
                         "medicine_id": {"$first": "$medicine_id"},
                         "symptom_name": {"$first": "$symptoms.name"},
                         "severity_score": {"$first": "$severity_score"},
                         "seriousness_criteria": {"$first": "$seriousness_criteria"},
                         "legacy_flag": {"$max": "$symptoms.is_critical"}}},
            # Stage 3: Group by drug and symptom to compute frequencies
            {
                "$group": {
                    "_id": {
                        "medicine_key": "$_id.medicine",
                        "symptom": "$_id.symptom"
                    },
                    "incident_count": {"$sum": 1},
                    "medicine_name": {"$first": "$medicine_name"},
                    "medicine_id": {"$first": "$medicine_id"},
                    "report_keys": {"$addToSet": "$_id.report"},
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
                    "medicine": "$medicine_name",
                    "medicine_id": 1,
                    "medicine_key": "$_id.medicine_key",
                    "symptom": "$_id.symptom",
                    "incident_count": 1,
                    "report_keys": 1,
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
        import copy, hashlib, json
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        def dated(start, end):
            return [{"$set": {"_report_date": {"$convert": {"input": "$reported_at", "to": "date", "onError": None, "onNull": None}}}},
                    {"$match": {"_report_date": {"$gte": start, "$lt": end}}}]
        previous = {}
        if window_days:
            cutoff = now - timedelta(days=window_days)
            previous_pipeline = copy.deepcopy(pipeline)
            for stage in previous_pipeline:
                if "incident_count" in stage.get("$match", {}):
                    stage["$match"] = {"incident_count": {"$gte": 1}}
            previous = {(str(r["medicine_key"]), r["symptom"]): r["incident_count"] for r in collection.aggregate(
                dated(now - timedelta(days=2 * window_days), cutoff) + previous_pipeline)}
            pipeline = dated(cutoff, now) + pipeline
        results = list(collection.aggregate(pipeline))
        from app.services.sql_service import sql_service
        catalog = {m["medicine_id"]: m for m in sql_service.get_all_medicines()}
        reviews = {r["_id"]: r for r in mongo_client.get_database()["signal_reviews"].find({}, {"history": 0})}

        # Enrich results with SafetyAuditor recommendations
        for row in results:
            row["medicine_key"] = str(row["medicine_key"])
            medicine = catalog.get(row.get("medicine_id"))
            row["medicine"] = medicine["commercial_name"] if medicine else row["medicine"]
            row["formulation"] = f"{medicine['generic_name']} {medicine['strength']}" if medicine else "Catalog identity unavailable for this historical record"
            report_keys = sorted(str(key) for key in row.pop("report_keys"))
            row["revision"] = hashlib.sha256(json.dumps([report_keys, row["incident_count"], row["avg_severity"], row["reported_serious_cases"]]).encode()).hexdigest()
            row["review_key"] = hashlib.sha256(json.dumps([row["medicine_key"], row["symptom"], window_days]).encode()).hexdigest()
            review = reviews.get(row["review_key"])
            if review:
                review = {k: v for k, v in review.items() if k != "_id"}
            row["review"] = review
            row["review_status"] = review["status"] if review and review["revision"] == row["revision"] else "NEEDS_REVIEW"
            row["previous_period_count"] = previous.get((row["medicine_key"], row["symptom"]), 0) if window_days else None
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

    def review_pattern(self, medicine_key, symptom, window_days, revision, status, notes, user):
        from datetime import datetime, timezone
        from app.utils.exceptions import PharmavigilException
        pattern = next((r for r in self.execute_safety_signal_detection_pipeline(1, 1, window_days)
                        if r["medicine_key"] == medicine_key and r["symptom"] == symptom), None)
        if not pattern or pattern["revision"] != revision:
            raise PharmavigilException("Reports changed. Refresh the patterns before saving this review.")
        review = {"revision": revision, "status": status, "notes": notes,
                  "reviewed_at": datetime.now(timezone.utc).isoformat(),
                  "reviewed_by": {k: user[k] for k in ("user_id", "username", "full_name")}}
        mongo_client.get_database()["signal_reviews"].update_one({"_id": pattern["review_key"]},
            {"$set": review, "$push": {"history": review}}, upsert=True)
        return review

    def search_clinical_reports(self, search_query: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Literal case-insensitive phrase search, with the same semantics on every deployment."""
        import re
        term = search_query.strip()
        if len(term) > 200 or page < 1 or not 1 <= page_size <= 100:
            raise ValueError('Invalid clinical search parameters.')
        query = {'$or': [{field: {'$regex': re.escape(term), '$options': 'i'}}
                         for field in ('clinical_notes', 'symptoms.name', 'medicine_name', 'batch_number', 'report_id')]} if term else {}
        collection = mongo_client.get_adverse_reports_collection()
        total = collection.count_documents(query, maxTimeMS=5000)
        items = list(collection.find(query, {'_id': 0}).sort([('reported_at', -1), ('report_id', 1)])
                     .skip((page - 1) * page_size).limit(page_size).max_time_ms(5000))
        return {'items': items, 'total': total, 'page': page, 'page_size': page_size}

    def search_clinical_notes_text(self, search_query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Compatibility helper for callers that need the first page only."""
        return self.search_clinical_reports(search_query, page_size=limit)['items']

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
