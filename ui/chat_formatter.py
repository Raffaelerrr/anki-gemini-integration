from __future__ import annotations

import html
import re
from typing import Any

from ..i18n import tr
from ..markdown_loader import get_markdown_converter
from .html_utils import render_code_block_header, render_field_table, seal_appended_html
from .theme import get_theme_colors

_FENCE_RE = re.compile(
    r"```[ \t]*([^\n`]*)\n(.*?)```",
    re.DOTALL,
)


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
        r'<span class="chat-code-inline">\1</span>',
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
        r'<span class="chat-code-inline">\1</span>',
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

    rendered = converter.convert(prose)
    converter.reset()
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
    )

    return render_field_table(
        header,
        f"<pre class='chat-code-pre' style='margin:0;background:transparent;'>"
        f"{safe_content}</pre>",
        header_bg=palette.code_block_bg,
        body_bg=palette.code_pre_bg,
    )


def format_gemini_reply_html(
    text: str,
    copy_store: dict[str, str],
    id_prefix: str,
    *,
    config: dict[str, Any] | None = None,
    endcap: bool = False,
) -> str:
    if not text.strip():
        return ""

    parts: list[str] = []
    last_end = 0
    block_index = 0

    for match in _FENCE_RE.finditer(text):
        before = text[last_end : match.start()]
        lang = (match.group(1) or "").strip().lower()
        content = match.group(2).strip()
        field_name = _field_name_before(before)

        if before.strip():
            prose = _strip_trailing_field_label(before, field_name) if field_name else before
            if prose.strip():
                parts.append(_render_markdown_prose(prose))

        if lang == "markdown" and not field_name:
            if content:
                parts.append(_render_markdown_prose(content))
            last_end = match.end()
            continue

        if not content:
            last_end = match.end()
            continue

        block_id = f"{id_prefix}-{block_index}"
        block_index += 1
        copy_store[block_id] = content
        parts.append(_render_code_block(field_name, content, block_id, config=config))
        last_end = match.end()

    tail = text[last_end:]
    if tail.strip():
        parts.append(_render_markdown_prose(tail))

    if parts:
        return seal_appended_html("".join(parts), endcap=endcap)

    return seal_appended_html(_render_markdown_prose(text), endcap=endcap)
