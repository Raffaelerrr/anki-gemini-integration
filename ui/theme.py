from __future__ import annotations

import html
from dataclasses import dataclass

from aqt.qt import (
    QColor,
    QFrame,
    QIcon,
    QPalette,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSize,
    QSizePolicy,
    Qt,
    QTextEdit,
    QToolButton,
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
    from .help_icons import expand_help_icons

    palette = colors or get_theme_colors()
    text = expand_help_icons(text)
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
    return f"color: {palette.msg_loading}; font-weight: bold; padding: 4px 0px;"


def wrapper_token_colors(*, colors: ThemeColors | None = None) -> tuple[str, str]:
    palette = colors or get_theme_colors()
    if is_night_mode():
        return "#e5e7eb", "#111827"
    return "#1f2933", "#f9fafb"


def wrapper_warning_stylesheet(*, colors: ThemeColors | None = None) -> str:
    palette = colors or get_theme_colors()
    return (
        f"background-color: {palette.msg_loading}; "
        f"color: {palette.chat_surface_bg}; "
        "font-size: 11px; font-weight: bold; "
        "padding: 4px 10px; border-radius: 4px;"
    )


ICON_BUTTON_SIZE = 22
ICON_BUTTON_ICON_SIZE = ICON_BUTTON_SIZE - 4
ICON_BUTTON_PLAIN_ICON_SIZE = ICON_BUTTON_SIZE
EMOJI_TOOLBAR_BUTTON_SIZE = ICON_BUTTON_SIZE + 2
EMOJI_TOOLBAR_BUTTON_WIDTH = EMOJI_TOOLBAR_BUTTON_SIZE + 4
ICON_BUTTON_FONT_SIZE = ICON_BUTTON_SIZE - 8


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
        " font-size: 14px;"
        " font-weight: bold;"
        " border: none;"
        " padding: 0px 0px 2px 0px;"
        " margin: 6px 8px 6px 0px;"
        f" min-width: {ICON_BUTTON_SIZE}px;"
        f" max-width: {ICON_BUTTON_SIZE}px;"
        f" min-height: {ICON_BUTTON_SIZE}px;"
        f" max-height: {ICON_BUTTON_SIZE}px;"
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


def apply_native_page_scroll_theme(
    scroll: QScrollArea,
    *,
    allow_horizontal_scroll: bool = True,
) -> None:
    """Page-level scroll areas: vertical scroll; horizontal optional."""
    palette = get_theme_colors()
    scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
        if allow_horizontal_scroll
        else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    scroll.setStyleSheet(
        "QScrollArea { background: transparent; }"
        + scrollbar_stylesheet(track_bg="transparent", colors=palette)
    )


def apply_native_text_edit_surface_theme(editor: QTextEdit | QPlainTextEdit) -> None:
    palette = get_theme_colors()
    surface = palette.chat_surface_bg
    surface_color = QColor(surface)
    text_color = QColor(palette.text)
    is_plain = isinstance(editor, QPlainTextEdit)
    auto_height = getattr(editor, "_auto_height_adjust", None) is not None
    widget_name = "QPlainTextEdit" if is_plain else "QTextEdit"
    editor.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    editor.setAutoFillBackground(True)
    editor.setFrameShape(QFrame.Shape.NoFrame)
    epal = editor.palette()
    epal.setColor(QPalette.ColorRole.Base, surface_color)
    epal.setColor(QPalette.ColorRole.Window, surface_color)
    epal.setColor(QPalette.ColorRole.Text, text_color)
    editor.setPalette(epal)
    editor.setStyleSheet(
        f"{widget_name} {{"
        f" background-color: {surface};"
        f" color: {palette.text};"
        " border: 1px solid transparent;"
        " border-radius: 3px;"
        " padding: 4px;"
        "}"
        f"{widget_name}:focus {{"
        f" border: 1px solid {palette.link};"
        f" background-color: {surface};"
        "}"
        + scrollbar_stylesheet(track_bg=surface, colors=palette)
    )
    if is_plain:
        pass
    elif auto_height:
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    if not auto_height:
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    editor.setMinimumWidth(0)
    if auto_height:
        editor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    else:
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


def configure_circular_icon_button(
    button: QPushButton | QToolButton,
    *,
    text: str | None = None,
    icon: QIcon | None = None,
    bordered: bool = True,
    size: int | None = None,
    width: int | None = None,
) -> None:
    button_size = size or ICON_BUTTON_SIZE
    button_width = width or button_size
    button.setFixedSize(button_width, button_size)
    button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    button.setContentsMargins(0, 0, 0, 0)
    has_icon = icon is not None and not icon.isNull()
    if size is not None:
        icon_dim = button_size - 4 if bordered else button_size
    else:
        icon_dim = ICON_BUTTON_ICON_SIZE if bordered else ICON_BUTTON_PLAIN_ICON_SIZE
    icon_size = QSize(icon_dim, icon_dim)
    if isinstance(button, QToolButton):
        button.setAutoRaise(not bordered)
        button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
            if has_icon
            else Qt.ToolButtonStyle.ToolButtonTextOnly
        )
    if has_icon:
        button.setText("")
        button.setIcon(icon)
        button.setIconSize(icon_size)
    elif text is not None:
        button.setIcon(QIcon())
        button.setText(text)
    button.setStyleSheet(
        info_button_stylesheet(
            icon_only=has_icon,
            bordered=bordered,
            size=size,
            width=width,
        )
    )


def configure_checkable_circular_icon_button(
    button: QPushButton | QToolButton,
    *,
    text: str | None = None,
    icon: QIcon | None = None,
    bordered: bool = True,
    size: int | None = None,
    width: int | None = None,
    highlight_checked: bool = True,
) -> None:
    button.setCheckable(True)
    has_icon = icon is not None and not icon.isNull()
    configure_circular_icon_button(
        button,
        text=text,
        icon=icon,
        bordered=bordered,
        size=size,
        width=width,
    )
    button.setStyleSheet(
        checkable_icon_button_stylesheet(
            icon_only=has_icon,
            bordered=bordered,
            size=size,
            width=width,
            highlight_checked=highlight_checked,
        )
    )


def checkable_icon_button_stylesheet(
    *,
    icon_only: bool = False,
    bordered: bool = True,
    size: int | None = None,
    width: int | None = None,
    highlight_checked: bool = True,
) -> str:
    base = info_button_stylesheet(
        icon_only=icon_only,
        bordered=bordered,
        size=size,
        width=width,
    )
    if not highlight_checked:
        checked = (
            "\nQPushButton:checked, QToolButton:checked,\n"
            "QPushButton:focus, QToolButton:focus,\n"
            "QPushButton:checked:focus, QToolButton:checked:focus {\n"
            "    background: transparent;\n"
            "    border: none;\n"
            "    outline: none;\n"
            "}\n"
        )
    elif bordered:
        checked = (
            "\nQPushButton:checked, QToolButton:checked {\n"
            "    background: palette(highlight);\n"
            "    border: 1px solid palette(highlight);\n"
            "}\n"
        )
    else:
        checked = (
            "\nQPushButton:checked, QToolButton:checked {\n"
            "    background: palette(highlight);\n"
            "    border-radius: 4px;\n"
            "}\n"
        )
    return base + checked


def info_button_stylesheet(
    *,
    icon_only: bool = False,
    bordered: bool = True,
    size: int | None = None,
    width: int | None = None,
) -> str:
    button_size = size or ICON_BUTTON_SIZE
    button_width = width or button_size
    radius = button_size // 2
    if size is not None:
        icon_dim = button_size - 4 if bordered else button_size
    else:
        icon_dim = ICON_BUTTON_ICON_SIZE if bordered else ICON_BUTTON_PLAIN_ICON_SIZE
    if bordered:
        chrome_rule = (
            f"    border: 1px solid palette(mid);\n"
            f"    border-radius: {radius}px;\n"
        )
        hover_rule = ""
    else:
        chrome_rule = (
            "    border: none;\n"
            "    background: transparent;\n"
            "    border-radius: 4px;\n"
        )
        hover_rule = (
            "\nQPushButton:hover, QToolButton:hover {\n"
            "    background: palette(midlight);\n"
            "}\n"
        )
    if icon_only:
        icon_rule = (
            f"    qproperty-iconSize: {icon_dim}px {icon_dim}px;\n"
            "    padding: 0px;\n"
        )
        font_size = ICON_BUTTON_FONT_SIZE
        font_weight = "bold"
        text_rule = ""
    else:
        emoji_inset = 2
        font_size = max(12, button_size - 10)
        font_weight = "normal"
        icon_rule = f"    padding: {emoji_inset}px;\n"
        text_rule = "    line-height: 1;\n"
    font_family = (
        '"Segoe UI Emoji", "Segoe UI", sans-serif'
        if not icon_only
        else '"Segoe UI", sans-serif'
    )
    return f"""
QPushButton, QToolButton {{
    font-weight: {font_weight};
    font-family: {font_family};
    font-size: {font_size}px;
    min-width: {button_width}px;
    max-width: {button_width}px;
    min-height: {button_size}px;
    max-height: {button_size}px;
    margin: 0px;
{chrome_rule}{icon_rule}    text-align: center;
{text_rule}}}
QToolButton::menu-indicator {{
    image: none;
    width: 0px;
    height: 0px;
    subcontrol-position: right center;
}}{hover_rule}"""


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
_ACTIVE_TOOLTIP_WIDGET: QWidget | None = None
INSTRUCTION_TOOLTIP_MAX_WIDTH = 360


def apply_widget_tooltip_palette(widget: QWidget) -> None:
    palette = get_theme_colors()
    widget_palette = widget.palette()
    widget_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(palette.text))
    widget_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(palette.chat_surface_bg))
    widget.setPalette(widget_palette)


def _tooltip_anchor_global_pos(widget: QWidget):
    from aqt.qt import QPoint

    rect = widget.rect()
    return widget.mapToGlobal(QPoint(rect.center().x(), rect.bottom()))


def show_themed_tooltip(widget: QWidget, global_pos=None) -> None:
    from aqt.qt import QLabel, QPoint, Qt

    global _ACTIVE_TOOLTIP_POPUP, _ACTIVE_TOOLTIP_WIDGET

    text = (widget.toolTip() or "").strip()
    if not text:
        return

    if _ACTIVE_TOOLTIP_POPUP is not None and _ACTIVE_TOOLTIP_WIDGET is widget:
        return

    hide_themed_tooltip()

    colors = get_theme_colors()
    popup = QLabel()
    if "<" in text:
        popup.setTextFormat(Qt.TextFormat.RichText)
    popup.setText(text)
    popup.setWordWrap(True)
    popup.setMaximumWidth(INSTRUCTION_TOOLTIP_MAX_WIDTH)
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
    anchor = _tooltip_anchor_global_pos(widget) if global_pos is None else global_pos
    if global_pos is None:
        popup.move(anchor + QPoint(-popup.width() // 2, 6))
    else:
        popup.move(anchor + QPoint(0, 12))
    popup.show()
    _ACTIVE_TOOLTIP_POPUP = popup
    _ACTIVE_TOOLTIP_WIDGET = widget


def hide_themed_tooltip() -> None:
    global _ACTIVE_TOOLTIP_POPUP, _ACTIVE_TOOLTIP_WIDGET
    if _ACTIVE_TOOLTIP_POPUP is None:
        _ACTIVE_TOOLTIP_WIDGET = None
        return
    _ACTIVE_TOOLTIP_POPUP.close()
    _ACTIVE_TOOLTIP_POPUP.deleteLater()
    _ACTIVE_TOOLTIP_POPUP = None
    _ACTIVE_TOOLTIP_WIDGET = None


def chat_edit_menu_button_stylesheet() -> str:
    return chat_toolbar_button_stylesheet(icon_only=False)


def chat_toolbar_button_stylesheet(*, icon_only: bool = True, checkable: bool = False) -> str:
    colors = get_theme_colors()
    button_size = ICON_BUTTON_SIZE
    radius = button_size // 2
    icon_dim = ICON_BUTTON_ICON_SIZE if icon_only else button_size - 6
    icon_pad = max(0, (button_size - icon_dim) // 2)
    if icon_only:
        icon_rule = (
            f"    qproperty-iconSize: {icon_dim}px {icon_dim}px;\n"
            f"    padding: {icon_pad}px;\n"
        )
        font_size = ICON_BUTTON_FONT_SIZE
        font_weight = "bold"
        text_rule = ""
        font_family = '"Segoe UI", sans-serif'
    else:
        font_size = max(13, button_size - 8)
        emoji_pad_top = max(0, (button_size - font_size) // 2 - 1)
        emoji_pad_bottom = max(0, button_size - font_size - emoji_pad_top)
        icon_rule = (
            f"    padding-top: {emoji_pad_top}px;\n"
            f"    padding-bottom: {emoji_pad_bottom}px;\n"
            "    padding-left: 0px;\n"
            "    padding-right: 0px;\n"
        )
        font_weight = "normal"
        text_rule = f"    line-height: {font_size}px;\n"
        font_family = '"Segoe UI Emoji", "Segoe UI", sans-serif'
    hover_bg = "rgba(255, 255, 255, 0.12)" if is_night_mode() else "rgba(0, 0, 0, 0.06)"
    base = f"""
QPushButton, QToolButton {{
    font-weight: {font_weight};
    font-family: {font_family};
    font-size: {font_size}px;
    min-width: {button_size}px;
    max-width: {button_size}px;
    min-height: {button_size}px;
    max-height: {button_size}px;
    margin: 0px;
    border: 1px solid {colors.text_muted};
    border-radius: {radius}px;
    background: {colors.panel_bg};
    text-align: center;
{icon_rule}{text_rule}}}
QPushButton:hover, QToolButton:hover {{
    background: {hover_bg};
    border-color: {colors.text_strong};
}}
QPushButton:disabled, QToolButton:disabled {{
    border-color: {colors.border};
    background: transparent;
    opacity: 0.45;
}}
QToolButton::menu-indicator {{
    image: none;
    width: 0px;
    height: 0px;
    subcontrol-position: right center;
}}"""
    if not checkable:
        return base
    return base + f"""
QPushButton:checked, QToolButton:checked,
QPushButton:checked:focus, QToolButton:checked:focus {{
    background: {colors.panel_bg};
    border: 1px solid {colors.text_muted};
    outline: none;
}}
QPushButton:checked:hover, QToolButton:checked:hover {{
    background: {hover_bg};
    border-color: {colors.text_strong};
}}"""


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
    from aqt.qt import QTimer

    from ..config import load_config
    from .settings_compact_controls import (
        apply_settings_text_edit_newlines,
        apply_text_edit_wrap,
    )

    config = load_config()
    show_newlines = bool(config.get("settings_show_text_newlines", False))
    wrap = bool(config.get("settings_wrap_text_editors", True))
    for editor in host.findChildren(QTextEdit):
        apply_native_text_edit_surface_theme(editor)
        apply_settings_text_edit_newlines(editor, show=show_newlines)
        apply_text_edit_wrap(editor, wrap=wrap)
        refresh_tokens = getattr(editor, "refresh_token_theme", None)
        if refresh_tokens is not None:
            refresh_tokens()
        adjust = getattr(editor, "_auto_height_adjust", None)
        if adjust is not None:
            QTimer.singleShot(0, adjust)
    for editor in host.findChildren(QPlainTextEdit):
        apply_native_text_edit_surface_theme(editor)
        apply_settings_text_edit_newlines(editor, show=show_newlines)
        apply_text_edit_wrap(editor, wrap=wrap)


def refresh_addon_theme() -> None:
    from .chat_dialog import refresh_chat_theme
    from .dev_playground_dialog import refresh_dev_playground_theme
    from .settings_dialog import refresh_settings_theme
    from .themed_windows import refresh_registered_themed_windows

    refresh_chat_theme()
    refresh_settings_theme()
    refresh_dev_playground_theme()
    refresh_registered_themed_windows()
