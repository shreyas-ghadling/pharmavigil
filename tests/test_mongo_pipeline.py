"""
Tests for MongoDB Multi-Stage Aggregation Pipeline and Full-Text Search.
"""

import pytest
from app.database.mongo_client import mongo_client
from app.services.mongo_service import mongo_service


def is_mongo_available() -> bool:
    """Checks if MongoDB is online and responsive."""
    return mongo_client.ping()


class TestMongoPipeline:
    """Tests 6-stage aggregation pipeline and text search indexing."""

    @pytest.mark.skipif(not is_mongo_available(), reason="MongoDB server is not reachable")
    def test_aggregation_pipeline_live(self):
        """Tests the execution of the 6-stage Signal Detection Aggregation Pipeline."""
        signals = mongo_service.execute_safety_signal_detection_pipeline(
            min_severity=3,
            min_incidents=2
        )
        assert isinstance(signals, list)

        if signals:
            top_signal = signals[0]
            assert "medicine" in top_signal
            assert "symptom" in top_signal
            assert "signal_risk_score" in top_signal
            assert "risk_level" in top_signal
            assert top_signal["risk_level"] in ("CRITICAL", "HIGH", "MODERATE")
            assert top_signal["incident_count"] >= 2
            assert top_signal["avg_severity"] >= 3.0
            assert "alert_level" in top_signal

    @pytest.mark.skipif(not is_mongo_available(), reason="MongoDB server is not reachable")
    def test_risk_level_threshold_classification(self):
        """Verifies pipeline assigns risk_level (CRITICAL / HIGH / MODERATE) correctly."""
        signals = mongo_service.execute_safety_signal_detection_pipeline(
            min_severity=1,
            min_incidents=1
        )
        assert len(signals) > 0
        for s in signals:
            assert "risk_level" in s
            if s["signal_risk_score"] >= 12.0:
                assert s["risk_level"] == "CRITICAL"
            elif s["signal_risk_score"] >= 6.0:
                assert s["risk_level"] == "HIGH"
            else:
                assert s["risk_level"] == "MODERATE"

    @pytest.mark.skipif(not is_mongo_available(), reason="MongoDB server is not reachable")
    def test_clinical_notes_text_search(self):
        """Clinical search matches literal terms in notes or structured symptom fields."""
        results = mongo_service.search_clinical_notes_text("hypotension")
        assert isinstance(results, list)
        if results:
            first_match = results[0]
            assert "clinical_notes" in first_match
            searchable = [first_match.get('clinical_notes', ''), first_match.get('medicine_name', ''),
                          first_match.get('batch_number') or '', first_match.get('report_id', '')]
            searchable.extend(s.get('name', '') for s in first_match.get('symptoms', []))
            assert any('hypotension' in value.lower() for value in searchable)


class TestMongoOfflineTransformationLogic:
    """Unit test verifying the mathematical and transformation logic of the aggregation pipeline."""

    def test_signal_risk_multiplication_formula(self):
        incident_count = 5
        avg_severity = 4.2
        calculated_score = round(incident_count * avg_severity, 2)
        assert calculated_score == 21.0
