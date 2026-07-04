from __future__ import annotations

from pathlib import Path

_ICONS_DIR = Path(__file__).resolve().parent / "icons"
_EYE_VISIBLE_SVG = _ICONS_DIR / "eye.svg"
_EYE_HIDDEN_SVG = _ICONS_DIR / "barred_eye.svg"


def _tint_svg(svg_text: str, color: str) -> str:
    tinted = svg_text.replace("currentColor", color)
    return tinted.replace("#000000", color)


def _svg_renderer_class():
    try:
        from PyQt6.QtSvg import QSvgRenderer

        return QSvgRenderer
    except ImportError:
        try:
            from PyQt5.QtSvg import QSvgRenderer

            return QSvgRenderer
        except ImportError:
            return None


def _render_svg_icon(svg_path: Path, *, color: str, size: int):
    from aqt.qt import QIcon, QPainter, QPixmap, Qt

    QSvgRenderer = _svg_renderer_class()
    if QSvgRenderer is None or not svg_path.is_file():
        return None

    from aqt.qt import QByteArray, QRectF

    svg_text = _tint_svg(svg_path.read_text(encoding="utf-8"), color)
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not renderer.isValid():
        return None

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    inset = 1
    bounds = size - 2 * inset
    renderer.render(painter, QRectF(inset, inset, bounds, bounds))
    painter.end()
    return QIcon(pixmap)


def _render_fallback_icon(*, visible: bool, size: int):
    from aqt.qt import QColor, QIcon, QPainter, QPen, QPixmap, Qt

    from .theme import get_theme_colors

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    color = QColor(get_theme_colors().text)
    outline = QPen(color)
    outline.setWidthF(max(1.2, size * 0.08))
    outline.setCapStyle(Qt.PenCapStyle.RoundCap)
    outline.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

    cx = size / 2
    cy = size / 2
    eye_w = size * 0.72
    eye_h = size * 0.38

    painter.setPen(outline)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(
        int(cx - eye_w / 2),
        int(cy - eye_h / 2),
        int(eye_w),
        int(eye_h),
    )

    pupil_r = size * 0.11
    painter.setBrush(color)
    painter.drawEllipse(
        int(cx - pupil_r),
        int(cy - pupil_r),
        int(pupil_r * 2),
        int(pupil_r * 2),
    )

    if not visible:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        slash = QPen(color)
        slash.setWidthF(max(1.4, size * 0.09))
        slash.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(slash)
        inset = size * 0.16
        painter.drawLine(int(inset), int(size - inset), int(size - inset), int(inset))

    painter.end()
    return QIcon(pixmap)


def visibility_icon(*, visible: bool, size: int = 18):
    from .theme import get_theme_colors

    svg_path = _EYE_VISIBLE_SVG if visible else _EYE_HIDDEN_SVG
    icon = _render_svg_icon(svg_path, color=get_theme_colors().text, size=size)
    if icon is not None:
        return icon
    return _render_fallback_icon(visible=visible, size=size)
