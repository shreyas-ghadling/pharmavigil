"""Review-priority rules and recommendations must agree."""
import pytest
from app.models.medicine import SafetyAuditor


@pytest.mark.parametrize("count,average,expected", [(2, 3, "HIGH"), (2, 4, "HIGH"), (3, 4, "CRITICAL"), (1, 1, "MODERATE")])
def test_one_priority_rule_for_every_label(count, average, expected):
    result = SafetyAuditor.evaluate_signal_alert("Example", "Nausea", count, average, 0)
    assert result["alert_level"] == SafetyAuditor.classify_priority(result["signal_risk_score"]) == expected


def test_legacy_symptom_flags_do_not_define_clinical_risk():
    result = SafetyAuditor.evaluate_signal_alert("Example", "Nausea", 2, 1, 2)
    assert result["alert_level"] == "MODERATE"
