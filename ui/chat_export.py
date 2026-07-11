from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .chat_messages import ChatMessage

_BLOCK_BREAK_RE = re.compile(
    r"</(?:p|div|tr|li|h[1-6]|table|pre)>",
    re.IGNORECASE,
)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def html_fragment_to_plain_text(fragment: str) -> str:
    """Convert chat body HTML to plain text for export."""
    if not fragment:
        return ""
    try:
        from aqt.qt import QTextDocument

        document = QTextDocument()
        document.setHtml(fragment)
        plain = document.toPlainText()
        if plain:
            return plain
    except Exception:
        pass

    text = _BR_RE.sub("\n", fragment)
    text = _BLOCK_BREAK_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    return html.unescape(text).strip()


def format_chat_messages_as_text(messages: list[ChatMessage]) -> str:
    """Serialize structured chat messages to a plain-text transcript."""
    lines: list[str] = []
    for message in messages:
        body = html_fragment_to_plain_text(message.body_html)
        lines.append(f"{message.label}:")
        if body:
            lines.append(body)
        lines.append("")
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def build_chat_export_header(
    config: dict[str, Any],
    *,
    api_history: list[dict[str, Any]] | None = None,
    exported_at: datetime | None = None,
) -> list[str]:
    from ..gemini_client import resolve_model, resolve_thinking_budget, trim_history
    from ..i18n import tr
    from ..prompt_inspection import PromptInspection

    max_turns = int(config.get("max_history_turns", 10))
    trimmed = trim_history(list(api_history or []), max_turns)
    inspection = PromptInspection(
        purpose="chat",
        model=resolve_model(config, "chat"),
        temperature=float(config.get("temperature_chat", 0.2)),
        thinking_budget=resolve_thinking_budget(config, "chat"),
        extra_metadata={
            "streaming": bool(config.get("chat_streaming", True)),
            "history_turns": len(trimmed) // 2 if trimmed else 0,
            "max_history_turns": max_turns,
        },
    )
    stamp = (exported_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        tr("chat.download.meta.header", config=config),
        tr("chat.download.meta.exported_at", config=config, timestamp=stamp),
    ]
    lines.extend(inspection.metadata_lines(config))
    return lines


def format_chat_export_text(
    messages: list[ChatMessage],
    config: dict[str, Any],
    *,
    api_history: list[dict[str, Any]] | None = None,
    exported_at: datetime | None = None,
) -> str:
    """Build a downloadable transcript with settings metadata and chat messages."""
    header_lines = build_chat_export_header(
        config,
        api_history=api_history,
        exported_at=exported_at,
    )
    body = format_chat_messages_as_text(messages)
    if not body.strip() and not header_lines:
        return ""

    parts: list[str] = []
    if header_lines:
        parts.append("\n".join(header_lines))
        parts.append("")
        parts.append("---")
        parts.append("")
    if body.strip():
        parts.append(body.rstrip("\n"))
    return "\n".join(parts) + "\n"


def default_chat_export_filename(*, now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%Y-%m-%d-%H%M%S")
    return f"anki-ai-chat-{stamp}.txt"


def default_chat_download_directory() -> Path:
    """First-time export folder when no directory has been saved yet."""
    try:
        from aqt.qt import QStandardPaths

        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        if documents:
            return Path(documents)
    except Exception:
        pass
    return Path.home() / "Documents"
