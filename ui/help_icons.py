from __future__ import annotations

import base64
from pathlib import Path

INLINE_HELP_ICON_DISPLAY_SIZE = 16
# Keep in sync with ICON_BUTTON_PLAIN_ICON_SIZE in theme.py (toolbar icon raster size).
_TOOLBAR_ICON_REFERENCE_PX = 22
# Supersample factor before downscaling to the on-screen pixel grid.
MIN_HELP_ICON_SUPERSAMPLE = 5.0

CHAT_TOOLBAR_HELP_ICON_KEYS = (
    "brain",
    "barred_brain",
    "pencil",
    "eye",
    "lens",
    "download",
    "plus",
    "stop",
    "priority",
)


def _device_pixel_ratio() -> float:
    try:
        from aqt.qt import QGuiApplication
    except ImportError:
        return 1.0

    app = QGuiApplication.instance()
    if app is None:
        return 1.0
    screen = app.primaryScreen()
    if screen is None:
        return 1.0
    return float(screen.devicePixelRatio())


def _help_icon_target_physical_pixels(
    display_size: int = INLINE_HELP_ICON_DISPLAY_SIZE,
) -> int:
    dpr = max(1.0, _device_pixel_ratio())
    return max(1, round(display_size * dpr))


def _help_icon_render_pixels(
    display_size: int = INLINE_HELP_ICON_DISPLAY_SIZE,
) -> int:
    physical = _help_icon_target_physical_pixels(display_size)
    dpr = _device_pixel_ratio()
    toolbar_scale = _TOOLBAR_ICON_REFERENCE_PX / max(display_size, 1)
    scale = max(
        MIN_HELP_ICON_SUPERSAMPLE,
        dpr * 3.0,
        toolbar_scale * MIN_HELP_ICON_SUPERSAMPLE,
    )
    return max(physical + 1, round(physical * scale))


def _finalize_help_icon_pixmap(pixmap, *, physical_size: int):
    from aqt.qt import Qt

    if pixmap.isNull():
        return pixmap
    if pixmap.width() == physical_size and pixmap.height() == physical_size:
        return pixmap
    return pixmap.scaled(
        physical_size,
        physical_size,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def inline_svg_img_html(
    svg_path: Path,
    *,
    display_size: int = INLINE_HELP_ICON_DISPLAY_SIZE,
    tint: str | None = None,
) -> str:
    from aqt.qt import QBuffer, QByteArray, QIODevice

    from .svg_icons import pixmap_from_svg

    physical_size = _help_icon_target_physical_pixels(display_size)
    render_size = _help_icon_render_pixels(display_size)
    pixmap = pixmap_from_svg(svg_path, render_size, tint=tint)
    if pixmap.isNull():
        return ""

    pixmap = _finalize_help_icon_pixmap(pixmap, physical_size=physical_size)
    if pixmap.isNull():
        return ""

    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not pixmap.toImage().save(buffer, "PNG"):
        return ""

    b64 = base64.b64encode(bytes(ba)).decode("ascii")
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'width="{display_size}" height="{display_size}" '
        f'style="display: inline-block; vertical-align: middle; '
        f'width: {display_size}px; height: {display_size}px;" '
        f'alt="" />'
    )


def _help_icon_html_by_key() -> dict[str, str]:
    from .svg_icons import (
        barred_brain_svg_path,
        brain_svg_path,
        download_svg_path,
        eye_svg_path,
        lens_svg_path,
        pencil_svg_path,
        plus_svg_path,
        priority_sign_svg_path,
        stop_sign_svg_path,
        theme_toolbar_icon_color,
    )

    themed = theme_toolbar_icon_color()
    return {
        "brain": inline_svg_img_html(brain_svg_path()),
        "barred_brain": inline_svg_img_html(barred_brain_svg_path()),
        "pencil": inline_svg_img_html(pencil_svg_path(), tint=themed),
        "eye": inline_svg_img_html(eye_svg_path(), tint=themed),
        "lens": inline_svg_img_html(lens_svg_path(), tint=themed),
        "download": inline_svg_img_html(download_svg_path(), tint=themed),
        "plus": inline_svg_img_html(plus_svg_path(), tint=themed),
        "stop": inline_svg_img_html(stop_sign_svg_path()),
        "priority": inline_svg_img_html(priority_sign_svg_path()),
    }


def expand_help_icons(html: str) -> str:
    for key, img_html in _help_icon_html_by_key().items():
        html = html.replace(f"{{icon:{key}}}", img_html)
    return html


def instruction_html(html: str) -> str:
    return expand_help_icons(html)


def set_instruction_tooltip(widget, html: str) -> None:
    from aqt.qt import QEvent, QObject, Qt

    widget.setToolTip(expand_help_icons(html))
    widget.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
    if getattr(widget, "_rich_instruction_tooltip_filter", None) is not None:
        return

    class _RichInstructionTooltipFilter(QObject):
        def eventFilter(self, obj, event):
            from .theme import hide_themed_tooltip, show_themed_tooltip

            event_type = event.type()
            if event_type in (
                QEvent.Type.Leave,
                QEvent.Type.HoverLeave,
                QEvent.Type.Hide,
                QEvent.Type.EnabledChange,
            ):
                hide_themed_tooltip()
                return False
            if event_type == QEvent.Type.ToolTip:
                text = (obj.toolTip() or "").strip()
                if not text:
                    hide_themed_tooltip()
                    return False
                show_themed_tooltip(obj)
                return True
            return False

    filt = _RichInstructionTooltipFilter(widget)
    widget.installEventFilter(filt)
    widget._rich_instruction_tooltip_filter = filt
