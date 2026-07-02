from __future__ import annotations

from dataclasses import dataclass

try:
    from aqt.theme import theme_manager
except ImportError:
    theme_manager = None


def is_night_mode() -> bool:
    if theme_manager is None:
        return False
    return bool(theme_manager.night_mode)


@dataclass(frozen=True)
class ThemeColors:
    text: str
    text_strong: str
    text_muted: str
    link: str
    border: str
    msg_you: str
    msg_gemini: str
    msg_system: str
    msg_error: str
    msg_loading: str
    code_inline_bg: str
    code_block_border: str
    code_block_bg: str
    code_label: str
    code_pre_bg: str
    panel_bg: str
    panel_border: str
    panel_text: str
    success: str
    error: str
    preview_accent: str
    preview_bg: str


_LIGHT = ThemeColors(
    text="#1f2933",
    text_strong="#111827",
    text_muted="#5f6c7b",
    link="#1565c0",
    border="#d0d7de",
    msg_you="#2e7d32",
    msg_gemini="#1565c0",
    msg_system="#7b1fa2",
    msg_error="#c62828",
    msg_loading="#ef6c00",
    code_inline_bg="rgba(27, 31, 35, 0.06)",
    code_block_border="#c5cae9",
    code_block_bg="rgba(92, 107, 192, 0.08)",
    code_label="#3949ab",
    code_pre_bg="rgba(27, 31, 35, 0.04)",
    panel_bg="#f6f8fa",
    panel_border="#d0d7de",
    panel_text="#2c3e50",
    success="#2e7d32",
    error="#c62828",
    preview_accent="#7b1fa2",
    preview_bg="rgba(123, 31, 162, 0.08)",
)

_DARK = ThemeColors(
    text="#e0e0e0",
    text_strong="#f5f5f5",
    text_muted="#9aa0a6",
    link="#64b5f6",
    border="#555555",
    msg_you="#4caf50",
    msg_gemini="#2196f3",
    msg_system="#9c27b0",
    msg_error="#f44336",
    msg_loading="#ff9800",
    code_inline_bg="rgba(255, 255, 255, 0.1)",
    code_block_border="#5c6bc0",
    code_block_bg="rgba(92, 107, 192, 0.08)",
    code_label="#9fa8da",
    code_pre_bg="rgba(0, 0, 0, 0.2)",
    panel_bg="rgba(255, 255, 255, 0.06)",
    panel_border="#555555",
    panel_text="#eceff1",
    success="#66bb6a",
    error="#ef5350",
    preview_accent="#9c27b0",
    preview_bg="rgba(156, 39, 176, 0.08)",
)


def get_theme_colors() -> ThemeColors:
    return _DARK if is_night_mode() else _LIGHT


def muted_hint_html(text: str, *, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return f"<span style='font-size: 11px; color: {palette.text_muted};'>{text}</span>"


def panel_widget_stylesheet(*, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return (
        f"background-color: {palette.panel_bg}; "
        f"border: 1px solid {palette.panel_border}; "
        "border-radius: 6px; padding: 8px;"
    )


def panel_content_html(text: str, *, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return (
        f"<div style='font-size: 11px; color: {palette.panel_text}; line-height: 1.4;'>"
        f"{text}"
        "</div>"
    )


def status_color_stylesheet(*, ok: bool, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    color = palette.success if ok else palette.error
    return f"color: {color}; font-size: 11px;"


def loading_label_stylesheet(*, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return f"color: {palette.msg_loading}; font-weight: bold; padding: 4px;"


def info_button_stylesheet() -> str:
    return """
QPushButton {
    font-weight: bold;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    border: 1px solid palette(mid);
    border-radius: 14px;
}
"""


def chat_document_stylesheet(*, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return (
        f"body {{ color: {palette.text}; }}"
        f"p {{ margin: 6px 0; }}"
        f"b, strong {{ font-weight: bold; color: {palette.text_strong}; }}"
        f"i, em {{ font-style: italic; }}"
        f"ul, ol {{ margin: 6px 0; padding-left: 20px; }}"
        f"li {{ margin: 3px 0; }}"
        f"a {{ color: {palette.link}; text-decoration: none; }}"
        f".chat-prose {{ margin: 6px 0; line-height: 1.45; color: {palette.text}; }}"
        f".chat-heading {{ font-weight: bold; margin: 12px 0 6px 0; color: {palette.text_strong}; }}"
        f".chat-heading-1 {{ font-size: 16px; }}"
        f".chat-heading-2 {{ font-size: 15px; }}"
        f".chat-heading-3 {{ font-size: 14px; }}"
        f".chat-heading-4 {{ font-size: 13px; }}"
        f".chat-hr {{ border: none; border-top: 1px solid {palette.border}; margin: 12px 0; }}"
        f".chat-code-inline {{ font-family: Consolas, monospace; "
        f"background: {palette.code_inline_bg}; padding: 1px 4px; border-radius: 3px; }}"
        f".chat-label-you {{ color: {palette.msg_you}; }}"
        f".chat-label-gemini {{ color: {palette.msg_gemini}; }}"
        f".chat-label-system {{ color: {palette.msg_system}; }}"
        f".chat-label-error {{ color: {palette.msg_error}; }}"
        f".chat-stream-text {{ color: {palette.text}; }}"
        f".chat-code-block {{ margin: 10px 0; border: 1px solid {palette.code_block_border}; "
        f"border-radius: 6px; background-color: {palette.code_block_bg}; padding: 8px; }}"
        f".chat-code-label {{ color: {palette.code_label}; }}"
        f".chat-code-copy {{ color: {palette.link}; text-decoration: none; margin-left: 8px; }}"
        f".chat-code-pre {{ margin: 0; white-space: pre-wrap; word-wrap: break-word; "
        f"font-family: Consolas, monospace; font-size: 11px; color: {palette.text}; "
        f"background-color: {palette.code_pre_bg}; padding: 8px; border-radius: 4px; }}"
        f".chat-preview-panel {{ background-color: {palette.preview_bg}; "
        f"border-left: 4px solid {palette.preview_accent}; padding: 12px; "
        f"margin: 14px 0 5px 0; font-size: 11px; border-radius: 4px; }}"
        f".chat-preview-panel, .chat-preview-panel * {{ background-color: transparent; }}"
        f".chat-field-block {{ margin-top: 12px; margin-bottom: 0px; line-height: 1.35; }}"
        f".chat-field-block:first-child {{ margin-top: 0px; }}"
        f".chat-field-title {{ font-weight: bold; display: block; margin: 0 0 4px 0; padding: 0; }}"
        f".chat-field-content {{ margin: 0; padding: 0; display: block; }}"
        f".chat-field-content p, .chat-field-content div, "
        f".chat-field-content ol, .chat-field-content ul {{ "
        f"margin-top: 0px; margin-bottom: 4px; padding-top: 0px; }}"
        f".chat-field-content > *:first-child {{ margin-top: 0px; padding-top: 0px; }}"
        f".chat-field-content > *:last-child {{ margin-bottom: 0px; padding-bottom: 0px; }}"
        f".chat-field-content p:last-child, .chat-field-content div:last-child {{ "
        f"margin-bottom: 0px; }}"
        f"code {{ font-family: Consolas, monospace; background: {palette.code_inline_bg}; "
        f"padding: 1px 4px; border-radius: 3px; }}"
        f"hr {{ border: none; border-top: 1px solid {palette.border}; margin: 12px 0; }}"
    )


def refresh_addon_theme() -> None:
    from .chat_dialog import refresh_chat_theme
    from .settings_dialog import refresh_settings_theme

    refresh_chat_theme()
    refresh_settings_theme()
