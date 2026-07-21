from __future__ import annotations

import html
import re
_CLOSING_TAG_NAMES = (
    "table",
    "thead",
    "tbody",
    "tfoot",
    "tr",
    "td",
    "th",
    "div",
    "ul",
    "ol",
    "li",
    "p",
    "pre",
)
_CLOSING_TAG_RE = re.compile(
    r"<\/?(" + "|".join(_CLOSING_TAG_NAMES) + r")\b[^>]*\/?>",
    re.IGNORECASE,
)


def closing_tags_suffix(fragment: str) -> str:
    """Append closing tags for block elements left open in pasted HTML."""
    stack: list[str] = []
    for match in _CLOSING_TAG_RE.finditer(fragment):
        token = match.group(0)
        tag = match.group(1).lower()
        if token.startswith("</"):
            if tag in stack:
                while stack and stack[-1] != tag:
                    stack.pop()
                if stack and stack[-1] == tag:
                    stack.pop()
            continue
        if token.rstrip().endswith("/>"):
            continue
        stack.append(tag)
    return "".join(f"</{tag}>" for tag in reversed(stack))


def html_endcap() -> str:
    """Full-width neutral strip that breaks Qt table/background inheritance."""
    from .theme import get_theme_colors

    reset_bg = get_theme_colors().chat_surface_bg
    return (
        f"<table class='chat-html-endcap' width='100%' border='0' cellspacing='0' "
        f"cellpadding='0' bgcolor='{reset_bg}'>"
        f"<tr><td style='font-size:4px;line-height:4px;'>&nbsp;</td></tr>"
        f"</table>"
    )


def seal_appended_html(html_fragment: str, *, endcap: bool = True) -> str:
    """Balance tags; optional endcap for legacy incremental HTML append."""
    if not html_fragment:
        return html_endcap() if endcap else ""
    suffix = closing_tags_suffix(html_fragment)
    if endcap:
        return html_fragment + suffix + html_endcap()
    return html_fragment + suffix


def render_code_block_header(
    label_html: str,
    block_id: str,
    *,
    copy_title: str,
    preview_title: str | None = None,
    copy_icon: str = "⧉",
    preview_icon: str = "◉",
) -> str:
    """Header row: label left, preview + copy icon links upper-right (Qt table layout)."""
    safe_copy_title = html.escape(copy_title, quote=True)
    actions = (
        f"<a href='copy:{block_id}' class='chat-code-copy' title='{safe_copy_title}'>"
        f"{copy_icon}</a>"
    )
    if preview_title:
        safe_preview_title = html.escape(preview_title, quote=True)
        actions = (
            f"<a href='preview:{block_id}' class='chat-code-preview' "
            f"title='{safe_preview_title}'>{preview_icon}</a>"
            f"<span class='chat-code-action-gap'>&nbsp;</span>"
            f"{actions}"
        )
    return (
        f"<table class='chat-code-header' width='100%' border='0' cellspacing='0' cellpadding='0'>"
        f"<tr>"
        f"<td valign='middle' style='padding:0;'>{label_html}</td>"
        f"<td valign='middle' align='right' style='padding:0;width:1%;white-space:nowrap;'>"
        f"{actions}"
        f"</td>"
        f"</tr>"
        f"</table>"
    )


def render_field_table(    header_html: str,
    body_html: str,
    *,
    header_bg: str,
    body_bg: str,
    body_class: str = "",
    spacer: str = "",
) -> str:
    body_class_attr = f" class='{body_class}'" if body_class else ""
    return (
        f"{spacer}"
        f"<table class='chat-code-block tex2jax_ignore' width='100%' border='0' cellspacing='0' "
        f"cellpadding='0' bgcolor='{body_bg}'>"
        f"<tr bgcolor='{header_bg}'><td valign='middle' style='padding:6px 8px;'>"
        f"{header_html}</td></tr>"
        f"<tr bgcolor='{body_bg}'><td valign='middle'{body_class_attr} "
        f"style='padding:6px 8px;'>{body_html}</td></tr>"
        f"</table>"
    )
