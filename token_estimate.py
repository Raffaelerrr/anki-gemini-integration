from __future__ import annotations

from typing import Any


def estimate_text_tokens(text: str) -> int:
    """Rough token count (~4 characters per token)."""
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def estimate_chat_request_tokens(
    user_payload: str,
    history: list[dict[str, Any]],
    *,
    system_instruction: str = "",
) -> int:
    """Rough input-token estimate for one Gemini chat request (~4 chars per token)."""
    total = estimate_text_tokens(system_instruction)
    for turn in history:
        for part in turn.get("parts", []):
            total += estimate_text_tokens(str(part.get("text") or ""))
    total += estimate_text_tokens(user_payload)
    return total
