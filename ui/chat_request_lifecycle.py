"""Chat request token / cancel gate (pure logic, offline-testable)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class ChatRequestGate:
    """Tracks in-flight chat requests and stale response tokens."""

    in_flight: bool = False
    token: int = 0
    cancel: threading.Event = field(default_factory=threading.Event)
    active_response: object | None = None

    def set_in_flight(self, active: bool = True) -> None:
        self.in_flight = active
        self.cancel.clear()
        if not active:
            self.active_response = None

    def issue_token(self) -> int:
        self.token += 1
        return self.token

    def invalidate(self) -> None:
        """Bump token so in-flight callbacks become stale (e.g. new conversation)."""
        self.token += 1

    def should_handle(self, request_token: int, *, closing: bool = False) -> bool:
        return (not closing) and request_token == self.token

    def request_cancel(self) -> bool:
        """Signal cancel for the in-flight request. Returns False if nothing in flight."""
        if not self.in_flight:
            return False
        self.cancel.set()
        response = self.active_response
        self.active_response = None
        if response is not None:
            close = getattr(response, "close", None)
            if callable(close):
                try:
                    close()
                except (OSError, RuntimeError, AttributeError):
                    pass
        return True

    def register_response(self, response: object | None) -> None:
        self.active_response = response

    def should_cancel(self) -> bool:
        return self.cancel.is_set()
