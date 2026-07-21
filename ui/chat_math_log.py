from __future__ import annotations

from typing import Any

from .note_math_preview import (
    _MATHJAX_JS,
    cleanup_note_preview_webview,
    mathjax_typeset_js,
    web_math_preview_available,
)

CHAT_LOG_ROOT_ID = "addon-chat-log"

_CHAT_LOG_CSS = """
#addon-chat-log mjx-mo > mjx-c,
#addon-chat-log mjx-mi > mjx-c,
#addon-chat-log mjx-mn > mjx-c,
#addon-chat-log mjx-ms > mjx-c,
#addon-chat-log mjx-mtext > mjx-c,
#addon-chat-log mjx-stretchy-h,
#addon-chat-log mjx-stretchy-v {
    clip-path: padding-box xywh(-1em -2px calc(100% + 2em) calc(100% + 4px));
}
#addon-chat-log mjx-c {
    overflow: visible !important;
}
"""

_COPY_CLICK_JS = """
document.addEventListener('click', function (event) {
    var link = event.target.closest('a[href^="copy:"], a[href^="preview:"]');
    if (!link) {
        return;
    }
    event.preventDefault();
    var href = link.getAttribute('href') || '';
    if (href.indexOf('copy:') === 0) {
        pycmd('addon-chat-copy:' + href.slice(5));
    } else if (href.indexOf('preview:') === 0) {
        pycmd('addon-chat-preview:' + href.slice(8));
    }
}, true);
"""


def chat_math_log_available() -> bool:
    return web_math_preview_available()


def create_chat_log_webview(parent: Any) -> Any:
    from aqt.webview import AnkiWebView, AnkiWebViewKind

    return AnkiWebView(parent=parent, kind=AnkiWebViewKind.PREVIEWER)


def load_chat_log_webview(
    web: Any,
    document_html: str,
    *,
    stylesheet: str = "",
) -> None:
    body = document_html or f'<div id="{CHAT_LOG_ROOT_ID}"></div>'
    if f'id="{CHAT_LOG_ROOT_ID}"' not in body:
        body = f'<div id="{CHAT_LOG_ROOT_ID}">{body}</div>'
    body += (
        f"<script>{mathjax_typeset_js(CHAT_LOG_ROOT_ID)}</script>"
        f"<script>{_COPY_CLICK_JS}</script>"
    )
    head = f"<style>{stylesheet}{_CHAT_LOG_CSS}</style>"
    web.stdHtml(
        body,
        css=[],
        js=list(_MATHJAX_JS),
        head=head,
        default_css=True,
    )


def cleanup_chat_log_webview(web: Any | None) -> None:
    cleanup_note_preview_webview(web)


def chat_log_scroll_to_bottom(web: Any) -> None:
    try:
        web.eval("window.scrollTo(0, document.body.scrollHeight);")
    except Exception:
        pass


def chat_log_scroll_to_last_gemini_label(web: Any) -> None:
    try:
        web.eval(
            "(function () {"
            " var labels = document.querySelectorAll('.chat-label-gemini');"
            " if (!labels.length) return;"
            " labels[labels.length - 1].scrollIntoView({block: 'start'});"
            "})();"
        )
    except Exception:
        pass


def chat_log_scroll_y(web: Any) -> int:
    try:
        value = web.eval("window.scrollY || 0")
        return int(value or 0)
    except Exception:
        return 0


def chat_log_set_scroll_y(web: Any, scroll_y: int) -> None:
    try:
        web.eval(f"window.scrollTo(0, {max(0, scroll_y)});")
    except Exception:
        pass
