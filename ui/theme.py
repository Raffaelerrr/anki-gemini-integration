from __future__ import annotations

import html
from dataclasses import dataclass

from aqt.qt import (
    QColor,
    QFrame,
    QPalette,
    QScrollArea,
    QSizePolicy,
    Qt,
    QTextEdit,
    QWidget,
)

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
    chat_surface_bg: str


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
    code_block_bg="#e8eaf6",
    code_label="#3949ab",
    code_pre_bg="#f3f4f6",
    panel_bg="#f6f8fa",
    panel_border="#d0d7de",
    panel_text="#2c3e50",
    success="#2e7d32",
    error="#c62828",
    preview_accent="#7b1fa2",
    chat_surface_bg="#ffffff",
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
    code_block_bg="#3a3f5c",
    code_label="#9fa8da",
    code_pre_bg="#353535",
    panel_bg="rgba(255, 255, 255, 0.06)",
    panel_border="#555555",
    panel_text="#eceff1",
    success="#66bb6a",
    error="#ef5350",
    preview_accent="#9c27b0",
    chat_surface_bg="#2b2b2b",
)


def get_theme_colors() -> ThemeColors:
    return _DARK if is_night_mode() else _LIGHT


def muted_hint_html(text: str, *, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return f"<span style='font-size: 11px; color: {palette.text_muted};'>{text}</span>"


def strong_label_html(text: str, *, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return f"<b style='color: {palette.text_strong};'>{text}</b>"


def field_name_label_html(name: str, *, colors: ThemeColors | None = None) -> str:
    return strong_label_html(html.escape(name), colors=colors)


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


def wrapper_warning_stylesheet(*, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return (
        f"background-color: {palette.msg_loading}; "
        f"color: {palette.chat_surface_bg}; "
        "font-size: 11px; font-weight: bold; "
        "padding: 4px 10px; border-radius: 4px;"
    )


def settings_stale_banner_stylesheet(*, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    bg = palette.msg_loading
    fg = palette.chat_surface_bg
    return (
        f"QWidget#settingsStaleBanner {{"
        f" background-color: {bg};"
        " border-radius: 4px;"
        "}"
        f" QLabel#settingsStaleBannerText {{"
        " background: transparent;"
        f" color: {fg};"
        " font-size: 11px;"
        " font-weight: bold;"
        " padding: 8px 0px 8px 10px;"
        "}"
        f" QPushButton#settingsStaleBannerClose {{"
        " background: transparent;"
        f" color: {fg};"
        " font-size: 16px;"
        " font-weight: bold;"
        " border: none;"
        " padding: 0px 0px 3px 0px;"
        " margin: 6px 8px 6px 0px;"
        " min-width: 28px;"
        " max-width: 28px;"
        " min-height: 28px;"
        " max-height: 28px;"
        "}"
        " QPushButton#settingsStaleBannerClose:hover {"
        " background-color: rgba(0, 0, 0, 0.12);"
        " border-radius: 4px;"
        "}"
    )


PANEL_BORDER_RADIUS = 4


def scrollbar_stylesheet(
    *,
    track_bg: str,
    colors: ThemeColors | None = None,
    include_corner: bool = True,
) -> str:
    palette = colors or get_theme_colors()
    rules = (
        f"QScrollBar:vertical {{"
        f" background: {track_bg};"
        " width: 12px;"
        " margin: 0px;"
        " border: none;"
        "}"
        f"QScrollBar::handle:vertical {{"
        f" background: {palette.border};"
        " min-height: 24px;"
        " border-radius: 4px;"
        " margin: 2px;"
        "}"
        f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{"
        " height: 0px;"
        " border: none;"
        " background: transparent;"
        "}"
        f"QScrollBar:horizontal {{"
        f" background: {track_bg};"
        " height: 12px;"
        " margin: 0px;"
        " border: none;"
        "}"
        f"QScrollBar::handle:horizontal {{"
        f" background: {palette.border};"
        " min-width: 24px;"
        " border-radius: 4px;"
        " margin: 2px;"
        "}"
        f"QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{"
        " width: 0px;"
        " border: none;"
        " background: transparent;"
        "}"
    )
    if include_corner:
        rules += (
            "QAbstractScrollArea::corner {"
            " background: transparent; border: none;"
            "}"
        )
    return rules


def apply_native_page_scroll_theme(scroll: QScrollArea) -> None:
    """Page-level scroll areas: show both axes when content overflows."""
    palette = get_theme_colors()
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setStyleSheet(
        "QScrollArea { background: transparent; }"
        + scrollbar_stylesheet(track_bg="transparent", colors=palette)
    )


def apply_native_text_edit_surface_theme(editor: QTextEdit) -> None:
    palette = get_theme_colors()
    surface = palette.chat_surface_bg
    surface_color = QColor(surface)
    text_color = QColor(palette.text)
    editor.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    editor.setAutoFillBackground(True)
    editor.setFrameShape(QFrame.Shape.NoFrame)
    epal = editor.palette()
    epal.setColor(QPalette.ColorRole.Base, surface_color)
    epal.setColor(QPalette.ColorRole.Window, surface_color)
    epal.setColor(QPalette.ColorRole.Text, text_color)
    editor.setPalette(epal)
    editor.setStyleSheet(
        "QTextEdit {"
        f" background-color: {surface};"
        f" color: {palette.text};"
        " border: 1px solid transparent;"
        " border-radius: 3px;"
        " padding: 4px;"
        "}"
        "QTextEdit:focus {"
        f" border: 1px solid {palette.link};"
        f" background-color: {surface};"
        "}"
        + scrollbar_stylesheet(track_bg=surface, colors=palette)
    )
    editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    editor.setMinimumWidth(0)
    editor.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        editor.sizePolicy().verticalPolicy(),
    )
    viewport = editor.viewport()
    if viewport is not None:
        viewport.setAutoFillBackground(True)
        vpal = viewport.palette()
        vpal.setColor(QPalette.ColorRole.Base, surface_color)
        viewport.setPalette(vpal)
        viewport.setStyleSheet(f"background-color: {surface};")


def apply_native_fields_scroll_theme(panel: QWidget, scroll: QScrollArea) -> None:
    """Rounded border scroll area for imported note preview field lists."""
    from aqt.qt import QFrame

    palette = get_theme_colors()
    border = "#000000" if not is_night_mode() else palette.border
    radius = PANEL_BORDER_RADIUS
    panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    panel.setAutoFillBackground(False)
    panel.setStyleSheet(
        "QWidget#nativeFieldsPanel {"
        " background: transparent;"
        " border: none;"
        "}"
    )
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    viewport = scroll.viewport()
    if viewport is not None:
        viewport.setAutoFillBackground(False)
        viewport.setStyleSheet("background: transparent;")
    scroll.setStyleSheet(
        _fields_scroll_inner_stylesheet(border=border, radius=radius, palette=palette)
    )


# Backward-compatible alias used by chat context panel.
apply_context_fields_panel_theme = apply_native_fields_scroll_theme


def _fields_scroll_inner_stylesheet(*, border: str | None, radius: int, palette) -> str:
    border_rule = ""
    if border is not None:
        border_rule = f" border: 1px solid {border}; border-radius: {radius}px;"
    return (
        "QScrollArea {"
        " background: transparent;"
        f"{border_rule}"
        "}"
        + scrollbar_stylesheet(track_bg="transparent", colors=palette)
    )


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


def tooltip_stylesheet(*, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return f"""
QToolTip {{
    color: {palette.text};
    background-color: {palette.chat_surface_bg};
    border: 1px solid {palette.border};
    padding: 4px 6px;
}}
"""


_ACTIVE_TOOLTIP_POPUP: QWidget | None = None


def apply_widget_tooltip_palette(widget: QWidget) -> None:
    palette = get_theme_colors()
    widget_palette = widget.palette()
    widget_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(palette.text))
    widget_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(palette.chat_surface_bg))
    widget.setPalette(widget_palette)


def show_themed_tooltip(widget: QWidget, global_pos) -> None:
    from aqt.qt import QLabel, QPoint, Qt

    global _ACTIVE_TOOLTIP_POPUP
    hide_themed_tooltip()

    text = (widget.toolTip() or "").strip()
    if not text:
        return

    colors = get_theme_colors()
    popup = QLabel(text)
    popup.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
    popup.setStyleSheet(
        "QLabel {"
        f" color: {colors.text};"
        f" background-color: {colors.chat_surface_bg};"
        f" border: 1px solid {colors.border};"
        " padding: 4px 8px;"
        " }"
    )
    popup.adjustSize()
    popup.move(global_pos + QPoint(0, 12))
    popup.show()
    _ACTIVE_TOOLTIP_POPUP = popup


def hide_themed_tooltip() -> None:
    global _ACTIVE_TOOLTIP_POPUP
    if _ACTIVE_TOOLTIP_POPUP is None:
        return
    _ACTIVE_TOOLTIP_POPUP.close()
    _ACTIVE_TOOLTIP_POPUP.deleteLater()
    _ACTIVE_TOOLTIP_POPUP = None


def visibility_toggle_button_stylesheet(*, size: int = 26, icon_size: int = 14) -> str:
    radius = size // 2
    inner = max(1, size - 2)
    pad = max(0, (inner - icon_size) // 2)
    return f"""
QToolButton#visibilityToggle, QPushButton#visibilityToggle {{
    padding: {pad}px;
    margin: 0px;
    min-width: {size}px;
    max-width: {size}px;
    min-height: {size}px;
    max-height: {size}px;
    border: 1px solid palette(mid);
    border-radius: {radius}px;
}}
"""


def chat_document_stylesheet(*, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return (
        f"body {{ color: {palette.text}; background: {palette.chat_surface_bg}; }}"
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
        f".chat-code-copy {{ color: {palette.link}; text-decoration: none; font-size: 15px; }}"
        f".chat-code-pre {{ margin: 0; white-space: pre-wrap; word-wrap: break-word; "
        f"font-family: Consolas, monospace; font-size: 11px; color: {palette.text}; "
        f"background-color: {palette.code_pre_bg}; padding: 8px; border-radius: 4px; }}"
        f".chat-message-wrap {{ border-collapse: collapse; margin: 0; padding: 0; }}"
        f".chat-code-block .chat-field-content, .chat-code-block .chat-field-content * "
        f"{{ background-color: transparent; }}"
        f".chat-field-content {{ white-space: pre-wrap; word-wrap: break-word; }}"
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


def refresh_native_text_edits_in(host: QWidget) -> None:
    for editor in host.findChildren(QTextEdit):
        apply_native_text_edit_surface_theme(editor)


def refresh_addon_theme() -> None:
    from .chat_dialog import refresh_chat_theme
    from .settings_dialog import refresh_settings_theme

    refresh_chat_theme()
    refresh_settings_theme()
