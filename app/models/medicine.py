"""
Domain Object-Oriented Models for Pharmavigil
Encapsulates business entities: Medicine, Batch, and SafetyAuditor with state machines and rule validation.
"""

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from app.utils.exceptions import ExpiredBatchDispenseError, RecalledBatchOperationError


class Medicine:
    """Represents a pharmaceutical formulation in the regulatory catalog."""

    def __init__(
        self,
        medicine_id: int,
        commercial_name: str,
        generic_name: str,
        dosage_form: str,
        strength: str,
        manufacturer_id: int,
        manufacturer_name: Optional[str] = None
    ):
        self.medicine_id = medicine_id
        self.commercial_name = commercial_name
        self.generic_name = generic_name
        self.dosage_form = dosage_form
        self.strength = strength
        self.manufacturer_id = manufacturer_id
        self.manufacturer_name = manufacturer_name

    def __repr__(self) -> str:
        return f"<Medicine id={self.medicine_id} name='{self.commercial_name}' ({self.generic_name}) {self.strength}>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "medicine_id": self.medicine_id,
            "commercial_name": self.commercial_name,
            "generic_name": self.generic_name,
            "dosage_form": self.dosage_form,
            "strength": self.strength,
            "manufacturer_id": self.manufacturer_id,
            "manufacturer_name": self.manufacturer_name
        }


class Batch:
    """
    Represents a specific manufactured production lot.
    Enforces expiry validation and recall status state transitions.
    """

    VALID_STATUSES = {"ACTIVE", "UNDER_INVESTIGATION", "RECALLED", "EXPIRED"}

    def __init__(
        self,
        batch_number: str,
        medicine_id: int,
        manufacturing_date: date,
        expiry_date: date,
        total_units_produced: int,
        recall_status: str = "ACTIVE",
        medicine: Optional[Medicine] = None
    ):
        if total_units_produced <= 0:
            raise ValueError(f"Total units produced must be positive, got {total_units_produced}.")
        if expiry_date <= manufacturing_date:
            raise ValueError(f"Expiry date ({expiry_date}) must be strictly after manufacturing date ({manufacturing_date}).")
        
        status_upper = recall_status.upper()
        if status_upper not in self.VALID_STATUSES:
            raise ValueError(f"Invalid recall status: {recall_status}. Must be one of {self.VALID_STATUSES}")

        self.batch_number = batch_number
        self.medicine_id = medicine_id
        self.manufacturing_date = manufacturing_date
        self.expiry_date = expiry_date
        self.total_units_produced = total_units_produced
        self.recall_status = status_upper
        self.medicine = medicine

    def is_expired(self, current_date: Optional[date] = None) -> bool:
        """Determines if the batch has passed its expiration date or is marked EXPIRED."""
        today = current_date or date.today()
        return self.recall_status == "EXPIRED" or today > self.expiry_date

    @property
    def effective_status(self) -> str:
        """Single source of truth for batch status: RECALLED, EXPIRED, or ACTIVE."""
        if self.recall_status == "RECALLED":
            return "RECALLED"
        if self.is_expired():
            return "EXPIRED"
        return self.recall_status

    def days_until_expiry(self, current_date: Optional[date] = None) -> int:
        """Returns the number of remaining shelf life days (negative if expired)."""
        today = current_date or date.today()
        return (self.expiry_date - today).days

    def is_expiring_soon(self, threshold_days: int = 30, current_date: Optional[date] = None) -> bool:
        """Checks if the batch expires within the specified warning window."""
        days_left = self.days_until_expiry(current_date)
        return 0 <= days_left <= threshold_days

    def validate_for_dispensing(self, current_date: Optional[date] = None) -> None:
        """
        Validates whether the batch can be safely dispensed or distributed.
        Raises domain exceptions if the batch is expired or recalled.
        """
        if self.recall_status in ("RECALLED", "UNDER_INVESTIGATION"):
            raise RecalledBatchOperationError(
                batch_number=self.batch_number,
                recall_status=self.recall_status
            )
        if self.is_expired(current_date):
            raise ExpiredBatchDispenseError(
                batch_number=self.batch_number,
                expiry_date=str(self.expiry_date)
            )

    def mark_under_investigation(self, reason: str = "") -> None:
        """Transitions batch to UNDER_INVESTIGATION status."""
        if self.recall_status == "RECALLED":
            raise RecalledBatchOperationError(
                batch_number=self.batch_number,
                recall_status="RECALLED",
                message=f"Cannot place already RECALLED batch '{self.batch_number}' under investigation."
            )
        self.recall_status = "UNDER_INVESTIGATION"

    def mark_recalled(self) -> None:
        """Transitions batch to RECALLED status, raising if already recalled."""
        if self.recall_status == "RECALLED":
            raise RecalledBatchOperationError(
                batch_number=self.batch_number,
                recall_status="RECALLED",
                message=f"Refusing recall: Batch '{self.batch_number}' is already RECALLED."
            )
        self.recall_status = "RECALLED"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_number": self.batch_number,
            "medicine_id": self.medicine_id,
            "manufacturing_date": str(self.manufacturing_date),
            "expiry_date": str(self.expiry_date),
            "total_units_produced": self.total_units_produced,
            "recall_status": self.effective_status,
            "is_expired": self.is_expired(),
            "days_left": self.days_until_expiry()
        }


class SafetyAuditor:
    """
    Encapsulates pharmacovigilance safety evaluation logic, signal calculations,
    and automated regulatory recall recommendations.
    """

    CRITICAL_SCORE_THRESHOLD = 12.0
    HIGH_SCORE_THRESHOLD = 6.0

    @classmethod
    def classify_priority(cls, score: float) -> str:
        """One project rule set for review priority, not clinical risk."""
        if score >= cls.CRITICAL_SCORE_THRESHOLD:
            return "CRITICAL"
        if score >= cls.HIGH_SCORE_THRESHOLD:
            return "HIGH"
        return "MODERATE"

    @staticmethod
    def calculate_signal_risk_score(incident_count: int, avg_severity: float) -> float:
        """Calculates composite pharmacovigilance signal risk score."""
        return round(float(incident_count) * float(avg_severity), 2)

    @classmethod
    def evaluate_signal_alert(
        cls,
        medicine_name: str,
        symptom: str,
        incident_count: int,
        avg_severity: float,
        critical_cases: int
    ) -> Dict[str, Any]:
        """
        Evaluates risk indicators against safety thresholds.
        Returns risk categorization and emergency action recommendation.
        """
        risk_score = cls.calculate_signal_risk_score(incident_count, avg_severity)
        
        level = cls.classify_priority(risk_score)

        if level == "CRITICAL":
            recommendation = (
                f"IMMEDIATE ACTION REQUIRED: High pharmacovigilance signal detected for {medicine_name} "
                f"({symptom}). Trigger emergency batch recall and initiate distribution quarantine."
            )
        elif level == "HIGH":
            recommendation = (
                f"SAFETY ADVISORY: Elevated symptom frequency for {medicine_name} ({symptom}). "
                f"Flag batch for clinical review and monitor patient intake."
            )
        else:
            recommendation = "Standard baseline surveillance; within acceptable tolerance levels."

        return {
            "medicine_name": medicine_name,
            "symptom": symptom,
            "incident_count": incident_count,
            "avg_severity": avg_severity,
            "critical_cases": critical_cases,
            "signal_risk_score": risk_score,
            "alert_level": level,
            "recommendation": recommendation
        }
