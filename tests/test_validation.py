"""
Unit Tests for Pydantic Input Validation, OOP Domain Models, and Custom Exceptions.
"""

from datetime import date, timedelta
import pytest
from pydantic import ValidationError

from app.models.schemas import (
    AdverseReportCreate,
    PatientDemographicsSchema,
    SymptomSchema,
    BatchIntakeSchema
)
from app.models.medicine import Medicine, Batch, SafetyAuditor
from app.utils.exceptions import (
    ExpiredBatchDispenseError,
    RecalledBatchOperationError,
    InvalidSeverityScoreError,
    DatabaseConnectionError,
    BatchMedicineMismatchError,
    UnauthorizedAccessError
)
from app.utils.auth import (
    get_allowed_portals,
    verify_portal_access,
    PORTAL_DOCTOR,
    PORTAL_PHARMACIST,
    PORTAL_ADMIN,
    ROLE_DOCTOR_PATIENT,
    ROLE_PHARMACIST,
    ROLE_SAFETY_OFFICER_ADMIN
)
from app.services.mongo_service import mongo_service
from app.services.sql_service import sql_service


class TestPydanticValidation:
    """Tests Pydantic boundary and formatting validation."""

    def test_valid_adverse_report(self):
        payload = {
            "batch_number": "BCH-PCM-9042",
            "medicine_id": 101,
            "medicine_name": "Cardiomax",
            "reporter_type": "HOSPITAL_DOCTOR",
            "patient_demographics": {
                "age": 45,
                "gender": "Female",
                "pre_existing_conditions": ["Hypertension"]
            },
            "symptoms": [
                {"name": "Severe Dizziness", "onset_minutes": 30, "is_critical": True}
            ],
            "severity_score": 4,
            "clinical_notes": "Patient recovered after resting."
        }
        report = AdverseReportCreate(**payload)
        assert report.batch_number == "BCH-PCM-9042"
        assert report.severity_score == 4
        assert report.report_id.startswith("ADR-")

    def test_invalid_severity_score_bounds(self):
        """Severity score must be between 1 and 5."""
        base_payload = {
            "batch_number": "BCH-PCM-9042",
            "medicine_id": 101,
            "medicine_name": "Cardiomax",
            "reporter_type": "PATIENT",
            "patient_demographics": {"age": 30, "gender": "Male"},
            "symptoms": [{"name": "Nausea", "onset_minutes": 10}],
            "severity_score": 6  # Out of bounds!
        }
        with pytest.raises((InvalidSeverityScoreError, ValidationError)):
            AdverseReportCreate(**base_payload)

        base_payload["severity_score"] = 0  # Also out of bounds!
        with pytest.raises((InvalidSeverityScoreError, ValidationError)):
            AdverseReportCreate(**base_payload)

    def test_invalid_patient_age_bounds(self):
        """Age must be between 0 and 120."""
        payload_negative = {
            "batch_number": "BCH-PCM-9042",
            "medicine_id": 101,
            "medicine_name": "Cardiomax",
            "reporter_type": "PATIENT",
            "patient_demographics": {"age": -5, "gender": "Female"},
            "symptoms": [{"name": "Nausea", "onset_minutes": 10}],
            "severity_score": 2
        }
        with pytest.raises(ValidationError):
            AdverseReportCreate(**payload_negative)

        payload_exceeded = {
            "batch_number": "BCH-PCM-9042",
            "medicine_id": 101,
            "medicine_name": "Cardiomax",
            "reporter_type": "PATIENT",
            "patient_demographics": {"age": 140, "gender": "Female"},
            "symptoms": [{"name": "Nausea", "onset_minutes": 10}],
            "severity_score": 2
        }
        with pytest.raises(ValidationError):
            AdverseReportCreate(**payload_exceeded)

    def test_invalid_batch_number_format(self):
        """Batch number must follow regex pattern BCH-XXX-XXXX."""
        invalid_payload = {
            "batch_number": "INVALID_BATCH_FORMAT_123",
            "medicine_id": 101,
            "medicine_name": "Cardiomax",
            "reporter_type": "PATIENT",
            "patient_demographics": {"age": 40, "gender": "Male"},
            "symptoms": [{"name": "Headache", "onset_minutes": 10}],
            "severity_score": 2
        }
        with pytest.raises(ValidationError):
            AdverseReportCreate(**invalid_payload)

    def test_batch_intake_expiry_after_manufacturing(self):
        """Expiry date must be strictly after manufacturing date."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        with pytest.raises(ValidationError):
            BatchIntakeSchema(
                batch_number="BCH-TEST-001",
                medicine_id=1,
                manufacturing_date=today,
                expiry_date=yesterday,
                total_units_produced=1000
            )


class TestDomainOOPModels:
    """Tests domain OOP models and custom exception triggers."""

    def test_batch_expiration_and_dispense_error(self):
        past_mfg = date(2023, 1, 1)
        past_exp = date(2024, 1, 1)
        batch = Batch(
            batch_number="BCH-EXP-0001",
            medicine_id=101,
            manufacturing_date=past_mfg,
            expiry_date=past_exp,
            total_units_produced=5000,
            recall_status="ACTIVE"
        )
        assert batch.is_expired() is True
        with pytest.raises(ExpiredBatchDispenseError):
            batch.validate_for_dispensing()

    def test_recalled_batch_operation_error(self):
        mfg = date.today() - timedelta(days=60)
        exp = date.today() + timedelta(days=300)
        batch = Batch(
            batch_number="BCH-REC-0002",
            medicine_id=102,
            manufacturing_date=mfg,
            expiry_date=exp,
            total_units_produced=10000,
            recall_status="RECALLED"
        )
        with pytest.raises(RecalledBatchOperationError):
            batch.validate_for_dispensing()

    def test_safety_auditor_risk_score(self):
        score = SafetyAuditor.calculate_signal_risk_score(incident_count=4, avg_severity=4.5)
        assert score == 18.0

        alert = SafetyAuditor.evaluate_signal_alert(
            medicine_name="Cardiomax",
            symptom="Acute Hypotension",
            incident_count=4,
            avg_severity=4.5,
            critical_cases=3
        )
        assert alert["alert_level"] == "CRITICAL"
        assert "IMMEDIATE ACTION REQUIRED" in alert["recommendation"]

    def test_batch_medicine_mismatch_exception(self):
        """Verifies BatchMedicineMismatchError domain exception properties."""
        err = BatchMedicineMismatchError(
            batch_number="BCH-NRC-1011",
            medicine_id=101,
            expected_medicine_id=102,
            message="Batch mismatch: BCH-NRC-1011 belongs to medicine 102, not 101."
        )
        assert err.batch_number == "BCH-NRC-1011"
        assert err.medicine_id == 101
        assert err.expected_medicine_id == 102
        assert "BCH-NRC-1011" in str(err)

    def test_server_side_rejects_mismatched_batch(self):
        """Verifies server-side rejection when a report uses a batch from another medicine."""
        # BCH-NRC-1011 belongs to medicine_id 102 (Neurocalm), but payload asserts medicine_id 101 (Cardiomax)
        mismatched_payload = {
            "batch_number": "BCH-NRC-1011",
            "medicine_id": 101,  # WRONG medicine!
            "medicine_name": "Cardiomax",
            "reporter_type": "HOSPITAL_DOCTOR",
            "patient_demographics": {
                "age": 50,
                "gender": "Female",
                "pre_existing_conditions": ["Hypertension"]
            },
            "symptoms": [
                {"name": "Severe Dizziness", "onset_minutes": 20, "is_critical": True}
            ],
            "severity_score": 4,
            "clinical_notes": "Testing server-side batch mismatch validation rejection."
        }
        with pytest.raises(BatchMedicineMismatchError) as exc_info:
            mongo_service.insert_adverse_report(mismatched_payload)

        assert "Batch 'BCH-NRC-1011'" in str(exc_info.value)
        assert "not selected medicine ID 101" in str(exc_info.value)

    def test_server_side_rejects_nonexistent_batch(self):
        """Verifies server-side rejection when a report uses a batch that does not exist in MySQL."""
        nonexistent_payload = {
            "batch_number": "BCH-FAKE-9999",  # Valid regex, but nonexistent in MySQL
            "medicine_id": 101,
            "medicine_name": "Cardiomax",
            "reporter_type": "HOSPITAL_DOCTOR",
            "patient_demographics": {"age": 42, "gender": "Male"},
            "symptoms": [{"name": "Nausea", "onset_minutes": 15}],
            "severity_score": 3,
            "clinical_notes": "Testing rejection of nonexistent batch."
        }
        with pytest.raises(BatchMedicineMismatchError) as exc_info:
            mongo_service.insert_adverse_report(nonexistent_payload)

        assert "does not exist in the database" in str(exc_info.value)

    def test_server_side_fails_closed_when_mysql_unreachable(self, monkeypatch):
        """Verifies fail-closed behavior: raises DatabaseConnectionError and does NOT insert report if MySQL is offline."""
        def mock_offline_get_batch(batch_number):
            raise DatabaseConnectionError("Mocked MySQL connection timeout outage.")

        monkeypatch.setattr(sql_service, "get_batch_by_number", mock_offline_get_batch)

        payload = {
            "batch_number": "BCH-PCM-9042",
            "medicine_id": 101,
            "medicine_name": "Cardiomax",
            "reporter_type": "HOSPITAL_DOCTOR",
            "patient_demographics": {"age": 55, "gender": "Female"},
            "symptoms": [{"name": "Severe Dizziness", "onset_minutes": 25}],
            "severity_score": 4,
            "clinical_notes": "Testing fail-closed offline rejection."
        }
        with pytest.raises(DatabaseConnectionError) as exc_info:
            mongo_service.insert_adverse_report(payload)

        assert "MySQL database is unreachable" in str(exc_info.value)

    def test_rbac_server_side_portal_permissions(self):
        """Verifies server-side portal access enforcement for doctor, pharmacist, and admin roles."""
        # 1. Doctor role: can ONLY access Doctor portal
        assert get_allowed_portals(ROLE_DOCTOR_PATIENT) == [PORTAL_DOCTOR]
        assert verify_portal_access(ROLE_DOCTOR_PATIENT, PORTAL_DOCTOR) is True
        with pytest.raises(UnauthorizedAccessError):
            verify_portal_access(ROLE_DOCTOR_PATIENT, PORTAL_PHARMACIST)
        with pytest.raises(UnauthorizedAccessError):
            verify_portal_access(ROLE_DOCTOR_PATIENT, PORTAL_ADMIN)

        # 2. Pharmacist role: can ONLY access Pharmacist portal
        assert get_allowed_portals(ROLE_PHARMACIST) == [PORTAL_PHARMACIST]
        assert verify_portal_access(ROLE_PHARMACIST, PORTAL_PHARMACIST) is True
        with pytest.raises(UnauthorizedAccessError):
            verify_portal_access(ROLE_PHARMACIST, PORTAL_DOCTOR)
        with pytest.raises(UnauthorizedAccessError):
            verify_portal_access(ROLE_PHARMACIST, PORTAL_ADMIN)

        # 3. Admin / Safety Officer role: can access ALL 3 portals
        assert get_allowed_portals(ROLE_SAFETY_OFFICER_ADMIN) == [PORTAL_DOCTOR, PORTAL_PHARMACIST, PORTAL_ADMIN]
        assert verify_portal_access(ROLE_SAFETY_OFFICER_ADMIN, PORTAL_DOCTOR) is True
        assert verify_portal_access(ROLE_SAFETY_OFFICER_ADMIN, PORTAL_PHARMACIST) is True
        assert verify_portal_access(ROLE_SAFETY_OFFICER_ADMIN, PORTAL_ADMIN) is True


