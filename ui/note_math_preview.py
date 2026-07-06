from __future__ import annotations

import html
import re
from typing import Any

from .note_fields import field_inner_html

_MATHJAX_JS = (
    "js/mathjax.js",
    "js/vendor/mathjax/tex-chtml-full.js",
)


def mathjax_typeset_js(root_id: str) -> str:
    return f"""
(function () {{
    var root = document.getElementById({root_id!r});
    if (!root || !window.MathJax || !MathJax.startup || !MathJax.startup.promise) {{
        return;
    }}
    MathJax.startup.promise
        .then(function () {{
            if (MathJax.typesetClear) {{
                MathJax.typesetClear();
            }}
            return MathJax.typesetPromise([root]);
        }})
        .catch(function (err) {{
            console.log("addon MathJax failed:", err);
        }});
}})();
"""


_TYPESET_JS = mathjax_typeset_js("addon-note-preview")

_SCRIPT_TAG_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_TEX_MACRO_RE = re.compile(r"\\(?:newcommand|renewcommand|def|DeclareMathOperator)\b")
_HIDDEN_MACRO_BLOCK_RE = re.compile(
    r"<(?:div|span)\b[^>]*>[\s\S]*?\\(?:newcommand|renewcommand|def|DeclareMathOperator)\b[\s\S]*?</(?:div|span)>",
    re.IGNORECASE,
)

_PREVIEW_CSS_BASE = """
#addon-note-preview {
    padding: 8px 10px 14px;
}
#addon-note-preview .mathjax-preamble {
    display: none;
}
#addon-note-preview .field-block {
    margin: 0;
}
#addon-note-preview .field-gap {
    height: 8px;
}
#addon-note-preview .field-name {
    margin: 0 0 2px;
}
#addon-note-preview .field-value {
    margin: 0 0 8px;
}
#addon-note-preview .empty-preview {
    opacity: 0.85;
}
/* Qt WebEngine can clip thin CHTML glyph strokes (e.g. the crossbar on "t"). */
#addon-note-preview mjx-mo > mjx-c,
#addon-note-preview mjx-mi > mjx-c,
#addon-note-preview mjx-mn > mjx-c,
#addon-note-preview mjx-ms > mjx-c,
#addon-note-preview mjx-mtext > mjx-c,
#addon-note-preview mjx-stretchy-h,
#addon-note-preview mjx-stretchy-v {
    clip-path: padding-box xywh(-1em -2px calc(100% + 2em) calc(100% + 4px));
}
#addon-note-preview mjx-c {
    overflow: visible !important;
}
"""


def _preview_css() -> str:
    try:
        from .theme import get_theme_colors

        palette = get_theme_colors()
        text_color = palette.text
        bg_color = palette.chat_surface_bg
    except Exception:
        text_color = "inherit"
        bg_color = "transparent"
    return (
        _PREVIEW_CSS_BASE.replace(
            "#addon-note-preview {",
            f"#addon-note-preview {{\n    color: {text_color};",
            1,
        )
        + f"\nbody {{ background: {bg_color}; }}\n"
    )


def _preview_head() -> str:
    return f"<style>{_preview_css()}</style>"


def web_math_preview_available() -> bool:
    try:
        from aqt import mw
        from aqt.webview import AnkiWebView  # noqa: F401

        return mw is not None
    except Exception:
        return False


def _looks_like_mathjax_script(script: str) -> bool:
    lowered = script.casefold()
    return any(
        token in lowered
        for token in ("mathjax", "macros", "newcommand", "getcomponents", "def")
    )


def extract_template_preamble_sections(text: str) -> list[str]:
    stripped = (text or "").strip()
    if not stripped:
        return []

    sections: list[str] = []
    for match in _SCRIPT_TAG_RE.finditer(stripped):
        block = match.group(0)
        if _looks_like_mathjax_script(block):
            sections.append(block)

    if _TEX_MACRO_RE.search(stripped):
        for match in _HIDDEN_MACRO_BLOCK_RE.finditer(stripped):
            sections.append(match.group(0))
        if not any(_TEX_MACRO_RE.search(section) for section in sections):
            before_fields = stripped.split("{{", 1)[0].strip()
            if _TEX_MACRO_RE.search(before_fields):
                sections.append(before_fields)

    return sections


def extract_notetype_mathjax_preamble(notetype_id: int | None) -> str:
    if not notetype_id:
        return ""
    try:
        from aqt import mw

        if mw is None or mw.col is None:
            return ""
        model = mw.col.models.get(notetype_id)
    except Exception:
        return ""

    seen: set[str] = set()
    parts: list[str] = []
    for template in model.get("tmpls") or []:
        for key in ("qfmt", "afmt"):
            for section in extract_template_preamble_sections(str(template.get(key) or "")):
                normalized = section.strip()
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    parts.append(normalized)
    return "\n".join(parts)


def resolve_mathjax_preview_preamble(
    config: dict[str, Any] | None,
    *,
    notetype_id: int | None,
) -> str:
    from ..i18n import effective_mathjax_preview_preamble

    template_preamble = extract_notetype_mathjax_preamble(notetype_id).strip()
    if template_preamble:
        return template_preamble
    return effective_mathjax_preview_preamble(config).strip()


def _prepare_field_html(value: str) -> str:
    prepared = field_inner_html(value)
    try:
        from aqt import mw

        if mw is not None:
            displayed = mw.prepare_card_text_for_display(prepared)
            if isinstance(displayed, str):
                prepared = displayed
    except Exception:
        pass
    return prepared


def build_note_preview_body(
    fields: list[tuple[str, str]],
    *,
    empty_message: str = "",
    mathjax_preamble: str = "",
) -> str:
    preamble = (mathjax_preamble or "").strip()
    field_blocks: list[str] = []
    for index, (name, value) in enumerate(fields):
        if not value.strip():
            continue
        if field_blocks:
            field_blocks.append('<div class="field-gap"></div>')
        field_blocks.append(
            '<div class="field-block">'
            f'<div class="field-name"><b>{html.escape(name)}</b></div>'
            f'<div class="field-value">{_prepare_field_html(value)}</div>'
            "</div>"
        )

    if not field_blocks and not preamble:
        message = html.escape(empty_message or "")
        return f'<div id="addon-note-preview"><div class="empty-preview">{message}</div></div>'

    parts = ['<div id="addon-note-preview">']
    if preamble:
        parts.append(f'<div class="mathjax-preamble">{preamble}</div>')
    if field_blocks:
        if preamble:
            parts.append('<div class="field-gap"></div>')
        parts.extend(field_blocks)
    parts.append("</div>")
    return "".join(parts)


def create_note_preview_webview(parent: Any) -> Any:
    from aqt.webview import AnkiWebView, AnkiWebViewKind

    return AnkiWebView(parent=parent, kind=AnkiWebViewKind.PREVIEWER)


def load_note_preview_webview(
    web: Any,
    fields: list[tuple[str, str]],
    *,
    empty_message: str = "",
    config: dict[str, Any] | None = None,
    notetype_id: int | None = None,
) -> None:
    preamble = resolve_mathjax_preview_preamble(config, notetype_id=notetype_id)
    body = build_note_preview_body(
        fields,
        empty_message=empty_message,
        mathjax_preamble=preamble,
    )
    body += f"<script>{_TYPESET_JS}</script>"
    web.stdHtml(
        body,
        css=[],
        js=list(_MATHJAX_JS),
        head=_preview_head(),
        default_css=True,
    )


def cleanup_note_preview_webview(web: Any | None) -> None:
    if web is None:
        return
    try:
        web.cleanup()
    except Exception:
        pass
