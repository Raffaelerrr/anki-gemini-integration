from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChatMessage:
    """One row in the chat log (label + HTML body, no outer wrapper)."""

    label_class: str
    label: str
    body_html: str
    trailing_spacer: bool = False
