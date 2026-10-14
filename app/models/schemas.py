"""
Pydantic Validation Schemas for Pharmavigil
Validates incoming request payloads, boundary constraints, and batch CSV imports.
"""

from datetime import date, datetime, timezone
import re
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from app.utils.exceptions import InvalidSeverityScoreError


class SymptomSchema(BaseModel):
    """Schema representing an individual clinical symptom."""
    name: str = Field(..., min_length=2, max_length=100, description="Name of the symptom")
    onset_minutes: Optional[int] = Field(..., ge=0, description="Minutes after medicine use, or null when onset is unknown")
    is_critical: bool = Field(default=False, description="Flag indicating if the symptom is medically critical")


class PatientDemographicsSchema(BaseModel):
    """Schema representing patient metadata."""
    age: int = Field(..., ge=0, le=120, description="Patient age in years [0, 120]")
    gender: Literal["Female", "Male", "Non-binary", "Other"] = Field(..., description="Reported patient gender")
    pre_existing_conditions: List[str] = Field(default_factory=list, description="List of pre-existing comorbidities")


class ReportSubmitterSchema(BaseModel):
    """Authenticated sender, distinct from the declared reporting source."""
    user_id: int = Field(gt=0)
    username: str
    full_name: str
    role: str


class AdverseReportCreate(BaseModel):
    """
    Schema for creating adverse drug reaction reports.
    Enforces strict input boundary validation for patient safety reporting.
    """
    report_id: Optional[str] = Field(default=None, description="Unique tracking identifier")
    batch_number: Optional[str] = Field(..., description="Known batch number, or null when the reporter does not know it")
    medicine_id: int = Field(..., gt=0, description="Referenced Medicine ID")
    medicine_name: str = Field(..., min_length=2, max_length=150, description="Commercial medicine name")
    reporter_type: Literal["HOSPITAL_DOCTOR", "PATIENT", "PHARMACIST"] = Field(
        ...,
        description="Source of the adverse event report"
    )
    patient_demographics: PatientDemographicsSchema
    symptoms: List[SymptomSchema] = Field(..., min_length=1, description="At least one observed symptom is required")
    severity_score: int = Field(..., description="Reported intensity on the project's 1 (mild) to 5 (very severe) scale, independent of seriousness")
    seriousness_criteria: Optional[List[Literal[
        "DEATH", "LIFE_THREATENING", "HOSPITALIZATION", "DISABILITY", "CONGENITAL_ANOMALY", "MEDICALLY_IMPORTANT"
    ]]] = Field(default=None, description="Reported serious outcomes; null means unknown, an empty list means none reported")
    hospital_id: Optional[int] = Field(default=None, gt=0, description="Reporting hospital identifier")
    clinical_notes: Optional[str] = Field(default="", max_length=2000, description="Doctor observations or patient notes")
    reported_at: Optional[str] = Field(default=None, description="ISO timestamp of submission")
    submitted_by: Optional[ReportSubmitterSchema] = None
    case_reference: Optional[str] = Field(default=None, min_length=2, max_length=80)
    submission_key: Optional[str] = None
    case_key: Optional[str] = None

    @field_validator("symptoms")
    @classmethod
    def distinct_symptoms(cls, symptoms):
        seen = set()
        for symptom in symptoms:
            symptom.name = " ".join(symptom.name.split())
            key = symptom.name.casefold()
            if len(key) < 2 or key in seen:
                raise ValueError("List each observed symptom once, with a meaningful name.")
            seen.add(key)
        return symptoms

    @field_validator("batch_number")
    @classmethod
    def validate_batch_number_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        pattern = r"^BCH-[A-Z0-9-]+$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid batch number format '{v}'. Must match pattern 'BCH-XXX-XXXX'.")
        return v

    @field_validator("severity_score")
    @classmethod
    def validate_severity_score_bounds(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise InvalidSeverityScoreError(score=v)
        return v

    @model_validator(mode="before")
    @classmethod
    def set_defaults_and_ids(cls, values: dict) -> dict:
        if isinstance(values, dict):
            if not values.get("report_id"):
                import uuid
                values["report_id"] = f"ADR-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
            if not values.get("reported_at"):
                values["reported_at"] = datetime.now(timezone.utc).isoformat()
        return values


class BatchIntakeSchema(BaseModel):
    """Schema for validating batch CSV imports and pharmacist stock intake."""
    batch_number: str = Field(..., description="Batch number (e.g. BCH-PCM-9042)")
    medicine_id: int = Field(..., gt=0, description="Referenced Medicine ID")
    manufacturing_date: date = Field(..., description="Date of manufacturing")
    expiry_date: date = Field(..., description="Date of product expiration")
    total_units_produced: int = Field(..., gt=0, description="Units produced in batch")
    recall_status: str = Field(default="ACTIVE", description="Initial lifecycle status")

    @field_validator("batch_number")
    @classmethod
    def validate_batch_regex(cls, v: str) -> str:
        pattern = r"^BCH-[A-Z0-9-]+$"
        if not re.match(pattern, v):
            raise ValueError(f"Batch number '{v}' must adhere to 'BCH-XXX-XXXX' format.")
        return v

    @model_validator(mode="after")
    def validate_expiry_after_manufacturing(self) -> "BatchIntakeSchema":
        if self.expiry_date <= self.manufacturing_date:
            raise ValueError(
                f"Expiry date ({self.expiry_date}) must be strictly later than manufacturing date ({self.manufacturing_date})."
            )
        return self


class BatchRecallRequest(BaseModel):
    """Schema for requesting an emergency batch recall."""
    batch_number: str = Field(..., min_length=3)
    reason: str = Field(..., min_length=5, max_length=255)
    recalled_by: str = Field(default="SAFETY_OFFICER_ADMIN", min_length=2, max_length=100)
