"""
tests/test_rca_validator.py
────────────────────────────
Unit tests for RCA validation and MTTR calculation.
Run with: pytest tests/ -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from app.workflow.rca_validator import validate_rca, calculate_mttr, RCAValidationError


def make_valid_rca(**overrides):
    """Helper: returns a valid RCA dict, with optional field overrides."""
    base = {
        "root_cause_category": "Network Partition",
        "fix_applied":         "Restarted the primary node and re-established quorum",
        "prevention_steps":    "Add automated quorum monitoring and alerting thresholds",
        "incident_start":      datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        "incident_end":        datetime(2024, 1, 1, 11, 30, tzinfo=timezone.utc),
    }
    base.update(overrides)
    return base


# ── Happy path ─────────────────────────────────────────────────────────────
class TestValidRCA:
    def test_valid_rca_passes(self):
        """A complete RCA should not raise."""
        validate_rca(make_valid_rca())   # no exception = pass

    def test_mttr_calculation(self):
        start = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        end   = datetime(2024, 1, 1, 11, 30, tzinfo=timezone.utc)
        assert calculate_mttr(start, end) == 90.0   # 90 minutes

    def test_mttr_partial_minutes(self):
        start = datetime(2024, 1, 1, 10, 0,  tzinfo=timezone.utc)
        end   = datetime(2024, 1, 1, 10, 45, tzinfo=timezone.utc)
        assert calculate_mttr(start, end) == 45.0


# ── Missing RCA ────────────────────────────────────────────────────────────
class TestMissingRCA:
    def test_none_rca_raises(self):
        with pytest.raises(RCAValidationError) as exc:
            validate_rca(None)
        assert "No RCA" in exc.value.reasons[0]


# ── Field validation ───────────────────────────────────────────────────────
class TestFieldValidation:
    def test_empty_root_cause_raises(self):
        with pytest.raises(RCAValidationError) as exc:
            validate_rca(make_valid_rca(root_cause_category=""))
        assert any("root_cause_category" in r for r in exc.value.reasons)

    def test_whitespace_root_cause_raises(self):
        with pytest.raises(RCAValidationError) as exc:
            validate_rca(make_valid_rca(root_cause_category="   "))
        assert any("root_cause_category" in r for r in exc.value.reasons)

    def test_short_fix_applied_raises(self):
        with pytest.raises(RCAValidationError) as exc:
            validate_rca(make_valid_rca(fix_applied="too short"))
        assert any("fix_applied" in r for r in exc.value.reasons)

    def test_short_prevention_steps_raises(self):
        with pytest.raises(RCAValidationError) as exc:
            validate_rca(make_valid_rca(prevention_steps="short"))
        assert any("prevention_steps" in r for r in exc.value.reasons)

    def test_multiple_errors_reported_together(self):
        """All errors should be reported at once, not just the first."""
        with pytest.raises(RCAValidationError) as exc:
            validate_rca(make_valid_rca(
                root_cause_category="",
                fix_applied="tiny",
            ))
        assert len(exc.value.reasons) >= 2

    def test_end_before_start_raises(self):
        rca = make_valid_rca(
            incident_start=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            incident_end=  datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        )
        with pytest.raises(RCAValidationError) as exc:
            validate_rca(rca)
        assert any("incident_end" in r for r in exc.value.reasons)

    def test_same_start_end_raises(self):
        t = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        with pytest.raises(RCAValidationError) as exc:
            validate_rca(make_valid_rca(incident_start=t, incident_end=t))
        assert any("incident_end" in r for r in exc.value.reasons)


# ── tests/test_state_machine.py ────────────────────────────────────────────
"""Unit tests for Work Item state machine."""
from app.workflow.state_machine import WorkItemStateMachine, Status


class TestStateMachine:
    def test_open_to_investigating(self):
        sm = WorkItemStateMachine(Status.OPEN)
        new_sm = sm.transition(Status.INVESTIGATING)
        assert new_sm.current == Status.INVESTIGATING

    def test_investigating_to_resolved(self):
        sm = WorkItemStateMachine(Status.INVESTIGATING)
        new_sm = sm.transition(Status.RESOLVED)
        assert new_sm.current == Status.RESOLVED

    def test_resolved_to_closed(self):
        sm = WorkItemStateMachine(Status.RESOLVED)
        new_sm = sm.transition(Status.CLOSED)
        assert new_sm.current == Status.CLOSED

    def test_cannot_skip_state(self):
        """Cannot go directly from OPEN to RESOLVED."""
        sm = WorkItemStateMachine(Status.OPEN)
        with pytest.raises(ValueError):
            sm.transition(Status.RESOLVED)

    def test_cannot_go_backward(self):
        """Cannot go from INVESTIGATING back to OPEN."""
        sm = WorkItemStateMachine(Status.INVESTIGATING)
        with pytest.raises(ValueError):
            sm.transition(Status.OPEN)

    def test_closed_is_terminal(self):
        """No transition allowed from CLOSED."""
        sm = WorkItemStateMachine(Status.CLOSED)
        with pytest.raises(ValueError):
            sm.transition(Status.OPEN)

    def test_allowed_transitions(self):
        sm = WorkItemStateMachine(Status.OPEN)
        assert sm.allowed_transitions() == [Status.INVESTIGATING]

    def test_transition_is_immutable(self):
        """transition() returns new instance, doesn't mutate original."""
        sm = WorkItemStateMachine(Status.OPEN)
        _ = sm.transition(Status.INVESTIGATING)
        assert sm.current == Status.OPEN   # original unchanged


# ── tests/test_debounce.py ────────────────────────────────────────────────
"""Unit tests for the debounce engine."""
import asyncio
from app.core.debounce import DebounceEngine


class TestDebounceEngine:
    @pytest.fixture
    def engine(self):
        return DebounceEngine()

    @pytest.mark.asyncio
    async def test_first_signal_creates_work_item(self, engine):
        should_create, existing_id = await engine.process("CACHE_01", {"error": "timeout"})
        assert should_create is True
        assert existing_id is None

    @pytest.mark.asyncio
    async def test_second_signal_does_not_create(self, engine):
        await engine.process("CACHE_01", {})
        await engine.set_work_item_id("CACHE_01", "fake-uuid")
        should_create, existing_id = await engine.process("CACHE_01", {})
        assert should_create is False
        assert existing_id == "fake-uuid"

    @pytest.mark.asyncio
    async def test_different_components_are_independent(self, engine):
        create_a, _ = await engine.process("DB_01", {})
        create_b, _ = await engine.process("API_01", {})
        assert create_a is True
        assert create_b is True

    @pytest.mark.asyncio
    async def test_set_work_item_id(self, engine):
        await engine.process("CACHE_01", {})
        await engine.set_work_item_id("CACHE_01", "some-uuid")
        _, existing = await engine.process("CACHE_01", {})
        assert existing == "some-uuid"
