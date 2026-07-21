from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any

from ..i18n import tr
from ..markdown_loader import get_markdown_converter
from .html_utils import render_code_block_header, render_field_table, seal_appended_html
from .theme import get_theme_colors


@dataclass(frozen=True)
class StoredCodeBlock:
    """Clipboard/preview payload for one chat field or code fence."""

    text: str
    label: str = ""


def stored_block_text(value: StoredCodeBlock | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, StoredCodeBlock):
        return value.text
    return str(value)


def stored_block_label(value: StoredCodeBlock | str | None) -> str:
    if isinstance(value, StoredCodeBlock):
        return (value.label or "").strip()
    return ""


_FENCE_RE = re.compile(
    r"```[ \t]*([^\n`]*)\n(.*?)```",
    re.DOTALL,
)
_BOLD_MARKER_RE = re.compile(r"\*\*")
_PARTIAL_HEADING_RE = re.compile(r"^#{1,6}$")
_MATH_DISPLAY_RE = re.compile(r"\\\[[\s\S]*?\\\]")
_MATH_INLINE_RE = re.compile(r"\\\([\s\S]*?\\\)")
_MATH_PLACEHOLDER_RE = re.compile(r"\uE000(\d+)\uE001")


def _math_placeholder(index: int) -> str:
    return f"\uE000{index}\uE001"


def _inline_backtick_shield(index: int) -> str:
    return f"\uE002{index}\uE003"


_INLINE_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_INLINE_BACKTICK_SHIELD_RE = re.compile(r"\uE002(\d+)\uE003")


def _shield_inline_backticks(text: str) -> tuple[str, list[str]]:
    stored: list[str] = []

    def repl(match: re.Match[str]) -> str:
        stored.append(match.group(0))
        return _inline_backtick_shield(len(stored) - 1)

    return _INLINE_BACKTICK_RE.sub(repl, text), stored


def _restore_inline_backticks(text: str, stored: list[str]) -> str:
    if not stored:
        return text

    def repl(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if 0 <= index < len(stored):
            return stored[index]
        return match.group(0)

    return _INLINE_BACKTICK_SHIELD_RE.sub(repl, text)


def _restore_inline_backticks_as_html(text: str, stored: list[str]) -> str:
    """Re-insert shielded ``code`` spans as escaped HTML (tags stay literal)."""
    if not stored:
        return text

    def repl(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if not (0 <= index < len(stored)):
            return match.group(0)
        original = stored[index]
        inner = original[1:-1] if len(original) >= 2 and original.startswith("`") else original
        return (
            '<span class="chat-code-inline tex2jax_ignore">'
            f"{html.escape(inner)}"
            "</span>"
        )

    return _INLINE_BACKTICK_SHIELD_RE.sub(repl, text)


def _escape_html_for_markdown_input(text: str) -> str:
    """Escape raw HTML so Markdown cannot emit live tags from model prose."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _protect_math_for_markdown(text: str) -> tuple[str, list[str]]:
    protected: list[str] = []

    def stash(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return _math_placeholder(len(protected) - 1)

    text = _MATH_DISPLAY_RE.sub(stash, text)
    text = _MATH_INLINE_RE.sub(stash, text)
    return text, protected


def _restore_math_for_markdown(text: str, protected: list[str]) -> str:
    if not protected:
        return text

    def restore(match: re.Match[str]) -> str:
        index = int(match.group(1))
        if 0 <= index < len(protected):
            return protected[index]
        return match.group(0)

    return _MATH_PLACEHOLDER_RE.sub(restore, text)


def _parse_field_label_line(line: str) -> str | None:
    line = line.strip()
    if not line:
        return None

    bold_match = re.match(r"^\*\*(.+?)\*\*:?\s*$", line)
    if bold_match:
        name = bold_match.group(1).strip()
        return name if _is_plausible_field_name(name) else None

    campo_match = re.match(r"^Campo\s*\[([^\]]+)\]\s*:?\s*$", line, re.IGNORECASE)
    if campo_match:
        return campo_match.group(1).strip()

    field_match = re.match(r"^Field\s*\[([^\]]+)\]\s*:?\s*$", line, re.IGNORECASE)
    if field_match:
        return field_match.group(1).strip()

    if not line.endswith(":"):
        return None

    name = line[:-1].strip()
    if not _is_plausible_field_name(name):
        return None
    return name


def _is_plausible_field_name(name: str) -> bool:
    if not name or len(name) > 40:
        return False
    if re.match(r"^\d+\.", name):
        return False
    if re.search(r"[.!?]", name):
        return False
    if len(name.split()) > 5:
        return False
    lowered = name.lower()
    if lowered.startswith("nota ") and any(char.isdigit() for char in name):
        return False
    return True


def _field_name_before(text: str) -> str | None:
    lines = text.rstrip().split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return None
    return _parse_field_label_line(lines[-1])


def prose_contains_labeled_field_fences(text: str) -> bool:
    """True if markdown already has Front:/Back:-style labeled code fences."""
    if not (text or "").strip():
        return False
    last_end = 0
    for match in _FENCE_RE.finditer(text):
        before = text[last_end : match.start()]
        if _field_name_before(before):
            return True
        last_end = match.end()
    return False


def _strip_trailing_field_label(text: str, field_name: str) -> str:
    lines = text.rstrip().split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return text

    last_label = _parse_field_label_line(lines[-1])
    if last_label and last_label.lower() == field_name.lower():
        lines.pop()
    return "\n".join(lines)


def _qt_compatible_html(rendered: str) -> str:
    for level in (1, 2, 3, 4):
        rendered = re.sub(
            rf"<h{level}>(.*?)</h{level}>",
            rf'<div class="chat-heading chat-heading-{level}">\1</div>',
            rendered,
            flags=re.DOTALL | re.IGNORECASE,
        )

    rendered = re.sub(
        r"<hr\s*/?>",
        '<hr class="chat-hr">',
        rendered,
        flags=re.IGNORECASE,
    )
    rendered = re.sub(r"<strong>(.*?)</strong>", r"<b>\1</b>", rendered, flags=re.DOTALL)
    rendered = re.sub(r"<em>(.*?)</em>", r"<i>\1</i>", rendered, flags=re.DOTALL)
    rendered = re.sub(
        r"<code>(.*?)</code>",
        r'<span class="chat-code-inline tex2jax_ignore">\1</span>',
        rendered,
        flags=re.DOTALL,
    )
    rendered = rendered.replace("<ul>", '<ul style="margin: 6px 0; padding-left: 20px;">')
    rendered = rendered.replace("<ol>", '<ol style="margin: 6px 0; padding-left: 20px;">')
    rendered = rendered.replace("<li>", '<li style="margin: 3px 0;">')
    rendered = rendered.replace("<p>", '<p style="margin: 6px 0;">')
    return rendered


def _render_prose_fallback(text: str) -> str:
    escaped = html.escape(text.strip())
    escaped = re.sub(
        r"^---+\s*$",
        '<hr class="chat-hr">',
        escaped,
        flags=re.MULTILINE,
    )
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped, flags=re.DOTALL)
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped, flags=re.DOTALL)
    escaped = re.sub(
        r"`([^`]+)`",
        r'<span class="chat-code-inline tex2jax_ignore">\1</span>',
        escaped,
    )
    escaped = re.sub(
        r"^### (.+)$",
        r'<div class="chat-heading chat-heading-3">\1</div>',
        escaped,
        flags=re.MULTILINE,
    )
    escaped = re.sub(
        r"^## (.+)$",
        r'<div class="chat-heading chat-heading-2">\1</div>',
        escaped,
        flags=re.MULTILINE,
    )
    escaped = escaped.replace("\n\n", "<br><br>")
    escaped = escaped.replace("\n", "<br>")
    return f'<div class="chat-prose">{escaped}</div>'


def _render_markdown_prose(text: str) -> str:
    prose = text.strip()
    if not prose:
        return ""

    converter = get_markdown_converter()
    if converter is None:
        return _render_prose_fallback(prose)

    markdown_input, inline_shields = _shield_inline_backticks(prose)
    markdown_input, protected = _protect_math_for_markdown(markdown_input)
    # Model prose often cites HTML tags (<b>, <ol>, …). Escape them so they stay
    # visible as text instead of becoming real markup (or vanishing).
    markdown_input = _escape_html_for_markdown_input(markdown_input)
    rendered = converter.convert(markdown_input)
    converter.reset()
    rendered = _restore_math_for_markdown(rendered, protected)
    rendered = _restore_inline_backticks_as_html(rendered, inline_shields)
    rendered = _qt_compatible_html(rendered)
    return f'<div class="chat-prose">{rendered}</div>'


def _render_code_block(
    label: str | None,
    content: str,
    block_id: str,
    *,
    config: dict[str, Any] | None = None,
) -> str:
    copy_title = tr("formatter.copy", config=config)
    preview_title = tr("formatter.preview", config=config)
    safe_content = html.escape(content.strip())
    palette = get_theme_colors()
    if label:
        safe_label = html.escape(label.strip())
        label_html = f"<b class='chat-code-label'>{safe_label}</b>"
    else:
        label_html = (
            f"<span class='chat-code-label'>{tr('formatter.code_block', config=config)}</span>"
        )

    header = render_code_block_header(
        label_html,
        block_id,
        copy_title=copy_title,
        preview_title=preview_title,
    )

    return render_field_table(
        header,
        f"<pre class='chat-code-pre' style='margin:0;background:transparent;'>"
        f"{safe_content}</pre>",
        header_bg=palette.code_block_bg,
        body_bg=palette.code_pre_bg,
    )


def _render_note_group(field_html_parts: list[str]) -> str:
    """Wrap consecutive labeled field blocks as one visual note unit."""
    if not field_html_parts:
        return ""
    if len(field_html_parts) == 1:
        return field_html_parts[0]
    palette = get_theme_colors()
    inner = "".join(field_html_parts)
    # Side gutters (not CSS padding) so nested width=100% field tables stay inset
    # inside the note frame in Qt/WebEngine table layout.
    return (
        f"<table class='chat-note-group' width='100%' border='0' cellspacing='0' "
        f"cellpadding='0' bgcolor='{palette.note_group_bg}'>"
        f"<tr>"
        f"<td class='chat-note-group-gutter' width='10' "
        f"style='width:10px;padding:0;line-height:0;'>&nbsp;</td>"
        f"<td class='chat-note-group-cell' style='padding:10px 0 6px 0;'>"
        f"{inner}"
        f"</td>"
        f"<td class='chat-note-group-gutter' width='10' "
        f"style='width:10px;padding:0;line-height:0;'>&nbsp;</td>"
        f"</tr></table>"
    )


def _split_at_open_fence(text: str) -> tuple[str, str]:
    """Keep prose and closed fences in *safe*; defer an opening ``` fence to plain text."""
    last_end = 0
    for match in _FENCE_RE.finditer(text):
        last_end = match.end()
    remainder = text[last_end:]
    fence_start = remainder.find("```")
    if fence_start >= 0:
        split_at = last_end + fence_start
        return text[:split_at], text[split_at:]
    return text, ""


def _single_backtick_positions(text: str) -> list[int]:
    positions: list[int] = []
    index = 0
    while index < len(text):
        if text.startswith("```", index):
            index += 3
            continue
        if text[index] == "`":
            positions.append(index)
        index += 1
    return positions


def _inline_unsafe_suffix_start(text: str) -> int | None:
    """Index where trailing inline markdown should stay plain until it completes."""
    if not text:
        return None

    unsafe_at: int | None = None

    bold_markers = list(_BOLD_MARKER_RE.finditer(text))
    if len(bold_markers) % 2 == 1:
        unsafe_at = bold_markers[-1].start()

    backticks = _single_backtick_positions(text)
    if len(backticks) % 2 == 1:
        unsafe_at = min(unsafe_at, backticks[-1]) if unsafe_at is not None else backticks[-1]

    lines = text.split("\n")
    last_line = lines[-1] if lines else ""
    if _PARTIAL_HEADING_RE.match(last_line):
        line_start = len(text) - len(last_line)
        unsafe_at = min(unsafe_at, line_start) if unsafe_at is not None else line_start

    return unsafe_at


def split_streaming_reply(text: str) -> tuple[str, str]:
    """Split streamed markdown into a renderable prefix and a plain-text tail."""
    if not text:
        return "", ""

    safe, tail = _split_at_open_fence(text)
    inline_start = _inline_unsafe_suffix_start(safe)
    if inline_start is not None:
        return safe[:inline_start], safe[inline_start:] + tail
    return safe, tail


def _escape_streaming_tail(text: str) -> str:
    if not text:
        return ""
    escaped = html.escape(text).replace("\n", "<br>")
    return f'<span class="chat-stream-text">{escaped}</span>'


def format_streaming_reply_html(
    text: str,
    copy_store: dict[str, str],
    id_prefix: str,
    *,
    config: dict[str, Any] | None = None,
) -> str:
    """Render completed markdown during streaming; keep incomplete syntax as plain text."""
    safe, tail = split_streaming_reply(text)
    parts: list[str] = []
    if safe.strip():
        formatted = format_gemini_reply_html(
            safe,
            copy_store,
            id_prefix,
            config=config,
            endcap=False,
        )
        if formatted:
            parts.append(formatted)
    if tail:
        parts.append(_escape_streaming_tail(tail))
    return "".join(parts)


def format_gemini_reply_html(
    text: str,
    copy_store: dict[str, StoredCodeBlock | str],
    id_prefix: str,
    *,
    config: dict[str, Any] | None = None,
    endcap: bool = False,
) -> str:
    if not text.strip():
        return ""

    parts: list[str] = []
    pending_fields: list[str] = []
    pending_labels: list[str] = []
    last_end = 0
    block_index = 0

    def flush_fields() -> None:
        if pending_fields:
            parts.append(_render_note_group(pending_fields))
            pending_fields.clear()
            pending_labels.clear()

    for match in _FENCE_RE.finditer(text):
        before = text[last_end : match.start()]
        lang = (match.group(1) or "").strip().lower()
        content = match.group(2).strip()
        field_name = _field_name_before(before)

        if before.strip():
            prose = _strip_trailing_field_label(before, field_name) if field_name else before
            if prose.strip():
                flush_fields()
                parts.append(_render_markdown_prose(prose))

        if lang == "markdown" and not field_name:
            flush_fields()
            if content:
                parts.append(_render_markdown_prose(content))
            last_end = match.end()
            continue

        if not content:
            last_end = match.end()
            continue

        block_id = f"{id_prefix}-{block_index}"
        block_index += 1
        copy_store[block_id] = StoredCodeBlock(
            text=content,
            label=(field_name or "").strip(),
        )
        block_html = _render_code_block(field_name, content, block_id, config=config)
        if field_name:
            label_key = field_name.casefold()
            if label_key in pending_labels:
                flush_fields()
            pending_fields.append(block_html)
            pending_labels.append(label_key)
        else:
            flush_fields()
            parts.append(block_html)
        last_end = match.end()

    flush_fields()
    tail = text[last_end:]
    if tail.strip():
        parts.append(_render_markdown_prose(tail))

    if parts:
        return seal_appended_html("".join(parts), endcap=endcap)

    return seal_appended_html(_render_markdown_prose(text), endcap=endcap)
