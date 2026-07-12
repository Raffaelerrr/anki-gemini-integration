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


MAX_CHAT_EXPORT_QUICK_FOLDERS = 5


def normalize_chat_export_quick_folders(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    folders: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        if not path:
            continue
        label = str(item.get("label") or "").strip() or Path(path).name
        folders.append({"label": label, "path": path})
    return folders[:MAX_CHAT_EXPORT_QUICK_FOLDERS]


def chat_export_last_used_directory(config: dict[str, Any]) -> Path | None:
    stored = str(config.get("chat_download_directory") or "").strip()
    if not stored:
        return None
    return Path(stored)


def format_export_folder_menu_text(
    path: str | Path,
    *,
    config: dict[str, Any],
    prefix_key: str,
    prefix_kwargs: dict[str, Any] | None = None,
) -> str:
    from ..i18n import tr

    display = _compact_path_label(path)
    kwargs = dict(prefix_kwargs or {})
    kwargs["folder"] = display
    return tr(prefix_key, config=config, **kwargs)


def _compact_path_label(path: str | Path, *, max_len: int = 56) -> str:
    text = str(path)
    if len(text) <= max_len:
        return text
    name = Path(path).name or text
    if len(name) >= max_len - 1:
        return f"…{name[-(max_len - 1):]}"
    return f"…{name}"


def resolve_chat_export_file_path(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    for index in range(1, 100):
        alternate = directory / f"{stem}-{index}{suffix}"
        if not alternate.exists():
            return alternate
    return directory / f"{stem}-{int(datetime.now().timestamp())}{suffix}"


def save_chat_export_text_to_directory(
    text: str,
    directory: Path,
    *,
    config: dict[str, Any] | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    export_path = resolve_chat_export_file_path(
        directory,
        default_chat_export_filename(),
    )
    export_path.write_text(text, encoding="utf-8")
    return export_path


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
