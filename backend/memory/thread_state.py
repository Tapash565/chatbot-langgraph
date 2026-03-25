"""Memory layer for conversation state management."""
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from backend.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ThreadState:
    """Represents the state of a conversation thread."""
    thread_id: str
    messages: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_updated: Optional[str] = None


class ThreadStateManager:
    """Manages thread state and checkpointing."""

    def __init__(self):
        self._states: Dict[str, ThreadState] = {}

    def get_state(self, thread_id: str) -> Optional[ThreadState]:
        """Get state for a thread."""
        return self._states.get(str(thread_id))

    def set_state(self, thread_id: str, state: ThreadState) -> None:
        """Set state for a thread."""
        self._states[str(thread_id)] = state

    def remove_state(self, thread_id: str) -> None:
        """Remove state for a thread."""
        self._states.pop(str(thread_id), None)

    def has_state(self, thread_id: str) -> bool:
        """Check if state exists for a thread."""
        return str(thread_id) in self._states


# Global state manager
thread_state_manager = ThreadStateManager()
