"""
workflow/rca_validator.py
──────────────────────────
Validates that an RCA is complete before allowing CLOSED transition.

RULES (all must pass):
  1. root_cause_category must be a non-empty string
  2. fix_applied must be a non-empty string (≥ 10 chars)
  3. prevention_steps must be a non-empty string (≥ 10 chars)
  4. incident_end must be AFTER incident_start
  5. RCA record must actually exist for the Work Item
"""
from datetime import datetime


class RCAValidationError(Exception):
    """Raised when RCA is missing or incomplete."""
    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__(f"RCA validation failed: {'; '.join(reasons)}")


def validate_rca(rca: dict | None) -> None:
    """
    Validate an RCA dictionary.
    Raises RCAValidationError with a list of all problems found.
    Call this before transitioning a Work Item to CLOSED.
    """
    if rca is None:
        raise RCAValidationError(["No RCA has been submitted for this incident"])

    errors: list[str] = []

    # 1. Root cause category
    category = (rca.get("root_cause_category") or "").strip()
    if not category:
        errors.append("root_cause_category is required")

    # 2. Fix applied (meaningful content required)
    fix = (rca.get("fix_applied") or "").strip()
    if len(fix) < 10:
        errors.append("fix_applied must be at least 10 characters")

    # 3. Prevention steps
    prevention = (rca.get("prevention_steps") or "").strip()
    if len(prevention) < 10:
        errors.append("prevention_steps must be at least 10 characters")

    # 4. Time range
    start = rca.get("incident_start")
    end   = rca.get("incident_end")
    if start and end:
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
        if end <= start:
            errors.append("incident_end must be after incident_start")
    else:
        errors.append("incident_start and incident_end are required")

    if errors:
        raise RCAValidationError(errors)


def calculate_mttr(start: datetime, end: datetime) -> float:
    """
    Mean Time To Repair in minutes.
    Formula: (end_time - start_time) in minutes
    """
    delta = end - start
    return round(delta.total_seconds() / 60, 2)
