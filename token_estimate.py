"""Payload size helpers for warnings and internal cache thresholds."""

from __future__ import annotations

from typing import Any


def payload_char_count(text: str) -> int:
    """Exact character count (Python ``len`` on the prompt text)."""
    return len(text or "")


def estimate_chat_request_chars(
    user_payload: str,
    history: list[dict[str, Any]],
    *,
    system_instruction: str = "",
) -> int:
    """Sum character counts for system text, history turns, and outgoing payload."""
    total = payload_char_count(system_instruction)
    for turn in history:
        for part in turn.get("parts", []):
            total += payload_char_count(str(part.get("text") or ""))
    total += payload_char_count(user_payload)
    return total


def estimate_text_tokens(text: str) -> int:
    """Internal rough token count for Gemini cache minimum checks only (~4 chars/token)."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)
