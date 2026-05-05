"""
workflow/state_machine.py
─────────────────────────
State Pattern for Work Item lifecycle.

States:   OPEN → INVESTIGATING → RESOLVED → CLOSED
Rules:
  - Transitions must follow the above order (no skipping).
  - CLOSED requires a complete RCA (enforced in the API layer).
  - CLOSED is terminal – no further transitions allowed.
"""
from enum import Enum


class Status(str, Enum):
    OPEN          = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED      = "RESOLVED"
    CLOSED        = "CLOSED"


# Allowed next states for each current state
TRANSITIONS: dict[Status, list[Status]] = {
    Status.OPEN:          [Status.INVESTIGATING],
    Status.INVESTIGATING: [Status.RESOLVED],
    Status.RESOLVED:      [Status.CLOSED],
    Status.CLOSED:        [],   # terminal
}


class WorkItemStateMachine:
    """
    Encapsulates state transition logic for a single Work Item.
    Instantiate with the current status, then call transition().
    """

    def __init__(self, current: Status):
        self.current = current

    def can_transition(self, target: Status) -> bool:
        return target in TRANSITIONS.get(self.current, [])

    def transition(self, target: Status) -> "WorkItemStateMachine":
        """
        Returns a NEW state machine instance with the target status.
        Raises ValueError if the transition is not allowed.
        """
        if not self.can_transition(target):
            raise ValueError(
                f"Invalid transition: {self.current} → {target}. "
                f"Allowed next states: {[s.value for s in TRANSITIONS[self.current]]}"
            )
        return WorkItemStateMachine(target)

    def allowed_transitions(self) -> list[Status]:
        return TRANSITIONS.get(self.current, [])

    def __repr__(self) -> str:
        return f"WorkItemStateMachine(current={self.current})"
