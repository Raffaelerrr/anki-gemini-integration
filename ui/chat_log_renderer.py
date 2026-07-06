from __future__ import annotations

import html

from .chat_messages import ChatMessage
from .theme import get_theme_colors


def render_chat_document(messages: list[ChatMessage]) -> str:
    """Build the full chat log HTML from structured messages."""
    if not messages:
        return ""

    surface = get_theme_colors().chat_surface_bg
    parts: list[str] = ['<div id="addon-chat-log">']
    for index, message in enumerate(messages):
        prefix = "<br>" if index else ""
        label = html.escape(message.label)
        inner = f"{prefix}<b class='{message.label_class}'>{label}:</b> {message.body_html}"
        if message.trailing_spacer:
            inner += "<div style='margin-bottom: 10px;'></div>"
        parts.append(
            f"<table class='chat-message-wrap' width='100%' border='0' "
            f"cellspacing='0' cellpadding='0' bgcolor='{surface}'>"
            f"<tr><td style='padding:0;'>{inner}</td></tr></table>"
        )
    parts.append("</div>")
    return "".join(parts)
