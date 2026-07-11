from __future__ import annotations

from pathlib import Path

from aqt.qt import (
    QColor,
    QPainter,
    QPen,
    Qt,
    QRectF,
    QStyle,
    QWidget,
)

from .theme import ICON_BUTTON_SIZE

_ICONS_DIR = Path(__file__).resolve().parent / "icons"
_EYE_SVG = "eye.svg"
_BARRED_EYE_SVG = "barred_eye.svg"


def visibility_icon_paths() -> tuple[Path, Path]:
    """Paths to the show/hide SVGs; replace these files with your own art."""
    return (_ICONS_DIR / _EYE_SVG, _ICONS_DIR / _BARRED_EYE_SVG)


def style_scrollbar_extent() -> int:
    from aqt.qt import QApplication

    app = QApplication.instance()
    if app is None:
        return 14
    try:
        metric = QStyle.PixelMetric.PM_ScrollBarExtent
    except AttributeError:
        metric = QStyle.PM_ScrollBarExtent
    return max(0, app.style().pixelMetric(metric))


def paint_vector_eye(
    painter: QPainter,
    rect: QRectF,
    *,
    color: str,
    visible: bool,
) -> None:
    cx = rect.center().x()
    cy = rect.center().y()
    eye_w = rect.width() * 0.86
    eye_h = rect.height() * 0.50
    eye_box = QRectF(cx - eye_w / 2, cy - eye_h / 2, eye_w, eye_h)

    outline = QPen(QColor(color))
    outline.setWidthF(1.25)
    outline.setCosmetic(True)
    outline.setCapStyle(Qt.PenCapStyle.RoundCap)
    outline.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

    painter.setPen(outline)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(eye_box)

    pupil_r = rect.width() * 0.12
    pupil = QRectF(cx - pupil_r, cy - pupil_r, pupil_r * 2, pupil_r * 2)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(pupil)

    if not visible:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        slash = QPen(QColor(color))
        slash.setWidthF(1.35)
        slash.setCosmetic(True)
        slash.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(slash)
        inset = min(rect.width(), rect.height()) * 0.18
        painter.drawLine(
            QRectF(rect.left() + inset, rect.bottom() - inset, 0, 0).topLeft(),
            QRectF(rect.right() - inset, rect.top() + inset, 0, 0).topLeft(),
        )


def _tint_svg(svg_text: str, color: str) -> str:
    """Replace currentColor / black strokes so QSvgRenderer paints the theme color."""
    tinted = svg_text.replace("currentColor", color)
    return tinted.replace("#000000", color)


def _load_svg_renderer(svg_path: Path, *, color: str):
    if not svg_path.is_file():
        return None
    try:
        from PyQt6.QtSvg import QSvgRenderer
    except ImportError:
        try:
            from PyQt5.QtSvg import QSvgRenderer  # type: ignore[no-redef]
        except ImportError:
            return None

    from aqt.qt import QByteArray

    svg_text = _tint_svg(svg_path.read_text(encoding="utf-8"), color)
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not renderer.isValid():
        return None
    return renderer


def _render_svg_icon(
    painter: QPainter,
    rect: QRectF,
    *,
    svg_path: Path,
    color: str,
) -> bool:
    renderer = _load_svg_renderer(svg_path, color=color)
    if renderer is None:
        return False

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, rect)
    painter.restore()
    return True


class VisibilityToggleButton(QWidget):
    """Circular show/hide toggle; paints border + vector eye in paintEvent."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        size: int = ICON_BUTTON_SIZE,
        on_click=None,
    ) -> None:
        super().__init__(parent)
        self._content_visible = True
        self._on_click = on_click
        self._size = size
        self._tooltip_text = ""
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def setToolTip(self, text: str) -> None:
        self._tooltip_text = text or ""

    def toolTip(self) -> str:
        return self._tooltip_text

    def enterEvent(self, event) -> None:
        from .theme import show_themed_tooltip
        from .widgets import _event_global_pos

        show_themed_tooltip(self, _event_global_pos(event))
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        from .theme import hide_themed_tooltip

        hide_themed_tooltip()
        super().leaveEvent(event)

    def set_content_visible(self, visible: bool) -> None:
        if self._content_visible != visible:
            self._content_visible = visible
            self.update()

    def paintEvent(self, event) -> None:
        from .theme import get_theme_colors, is_night_mode

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        palette = get_theme_colors()
        border_color = "#000000" if not is_night_mode() else palette.border
        fg = palette.text

        side = float(min(self.width(), self.height()))
        ring = QRectF(2.0, 2.0, side - 4.0, side - 4.0)

        border_pen = QPen(QColor(border_color))
        border_pen.setWidthF(1.0)
        border_pen.setCosmetic(True)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(ring)

        eye_rect = ring.adjusted(
            ring.width() * 0.20,
            ring.height() * 0.24,
            -ring.width() * 0.20,
            -ring.height() * 0.24,
        )
        show_path, hide_path = visibility_icon_paths()
        svg_path = show_path if self._content_visible else hide_path
        if not _render_svg_icon(painter, eye_rect, svg_path=svg_path, color=fg):
            paint_vector_eye(
                painter,
                eye_rect,
                color=fg,
                visible=self._content_visible,
            )
        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_clicked()
        super().mousePressEvent(event)

    def on_clicked(self) -> None:
        if self._on_click is not None:
            self._on_click()

    def sizeHint(self):
        from aqt.qt import QSize

        return QSize(self._size, self._size)
