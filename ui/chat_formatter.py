from __future__ import annotations

import html
import re

from ..markdown_loader import get_markdown_converter

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
        line = bold_match.group(1).strip()

    campo_match = re.match(r"^Campo\s*\[([^\]]+)\]\s*:?\s*$", line, re.IGNORECASE)
    if campo_match:
        return campo_match.group(1).strip()

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
    for level, size in ((1, 16), (2, 15), (3, 14), (4, 13)):
        rendered = re.sub(
            rf"<h{level}>(.*?)</h{level}>",
            rf'<div style="font-weight: bold; font-size: {size}px; margin: 12px 0 6px 0; color: #eceff1;">\1</div>',
            rendered,
            flags=re.DOTALL | re.IGNORECASE,
        )

    rendered = re.sub(
        r"<hr\s*/?>",
        '<hr style="border: none; border-top: 1px solid #555; margin: 12px 0;">',
        rendered,
        flags=re.IGNORECASE,
    )
    rendered = re.sub(r"<strong>(.*?)</strong>", r"<b>\1</b>", rendered, flags=re.DOTALL)
    rendered = re.sub(r"<em>(.*?)</em>", r"<i>\1</i>", rendered, flags=re.DOTALL)
    rendered = re.sub(
        r"<code>(.*?)</code>",
        r'<span style="font-family: Consolas, monospace; background: rgba(255,255,255,0.1); '
        r'padding: 1px 4px; border-radius: 3px;">\1</span>',
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
        '<hr style="border: none; border-top: 1px solid #555; margin: 12px 0;">',
        escaped,
        flags=re.MULTILINE,
    )
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped, flags=re.DOTALL)
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped, flags=re.DOTALL)
    escaped = re.sub(
        r"`([^`]+)`",
        r'<span style="font-family: Consolas, monospace; background: rgba(255,255,255,0.1); '
        r'padding: 1px 4px; border-radius: 3px;">\1</span>',
        escaped,
    )
    escaped = re.sub(
        r"^### (.+)$",
        r'<div style="font-weight: bold; margin-top: 10px;">\1</div>',
        escaped,
        flags=re.MULTILINE,
    )
    escaped = re.sub(
        r"^## (.+)$",
        r'<div style="font-weight: bold; font-size: 13px; margin-top: 12px;">\1</div>',
        escaped,
        flags=re.MULTILINE,
    )
    escaped = escaped.replace("\n\n", "<br><br>")
    escaped = escaped.replace("\n", "<br>")
    return f'<div style="margin: 6px 0; line-height: 1.45; color: #e0e0e0;">{escaped}</div>'


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
    return f'<div style="margin: 6px 0; line-height: 1.45; color: #e0e0e0;">{rendered}</div>'


def _render_code_block(label: str | None, content: str, block_id: str) -> str:
    safe_content = html.escape(content.strip())
    if label:
        safe_label = html.escape(label.strip())
        header = (
            f"<b style='color: #9fa8da;'>{safe_label}</b> "
            f"<a href='copy:{block_id}' style='color: #64b5f6; text-decoration: none; "
            f"margin-left: 8px;'>Copia</a>"
        )
    else:
        header = (
            f"<span style='color: #9fa8da;'>Blocco code</span> "
            f"<a href='copy:{block_id}' style='color: #64b5f6; text-decoration: none; "
            f"margin-left: 8px;'>Copia</a>"
        )

    return (
        "<div style='margin: 10px 0; border: 1px solid #5c6bc0; border-radius: 6px; "
        "background-color: rgba(92, 107, 192, 0.08); padding: 8px;'>"
        f"<div style='margin-bottom: 6px;'>{header}</div>"
        f"<pre style='margin: 0; white-space: pre-wrap; word-wrap: break-word; "
        f"font-family: Consolas, monospace; font-size: 11px; color: #e0e0e0; "
        f"background-color: rgba(0, 0, 0, 0.2); padding: 8px; border-radius: 4px;'>"
        f"{safe_content}</pre>"
        "</div>"
    )


def format_gemini_reply_html(
    text: str,
    copy_store: dict[str, str],
    id_prefix: str,
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
        parts.append(_render_code_block(field_name, content, block_id))
        last_end = match.end()

    tail = text[last_end:]
    if tail.strip():
        parts.append(_render_markdown_prose(tail))

    if parts:
        return "".join(parts)

    return _render_markdown_prose(text)
