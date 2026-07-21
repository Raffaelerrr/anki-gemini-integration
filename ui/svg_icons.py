from __future__ import annotations

from pathlib import Path

from aqt.qt import QIcon, QPainter, QPixmap, Qt, QRectF, QTransform, QWidget

from .theme import ICON_BUTTON_PLAIN_ICON_SIZE, get_theme_colors

_ICONS_DIR = Path(__file__).resolve().parent / "icons"
_STOP_SVG = "stop.svg"
_PRIORITY_SVG = "priority.svg"
_EYE_SVG = "eye.svg"
_PLUS_SVG = "plus.svg"
_BRAIN_SVG = "brain.svg"
_BARRED_BRAIN_SVG = "barred_brain.svg"
_CHAT_SVG = "chat.svg"
_SETTINGS_SVG = "settings.svg"
_UNDO_SVG = "undo.svg"
_LENS_SVG = "lens.svg"
_PENCIL_SVG = "pencil.svg"
_ROBOT_SVG = "robot.svg"
_STOP_CIRCLE_SVG = "stop_circle.svg"
_CACHE_SVG = "cache.svg"
_DOWNLOAD_SVG = "download.svg"
_IMPORT_SVG = "import.svg"
LOADING_STATUS_ICON_SIZE = 18

def icons_dir() -> Path:
    return _ICONS_DIR


def stop_sign_svg_path() -> Path:
    return _ICONS_DIR / _STOP_SVG


def priority_sign_svg_path() -> Path:
    return _ICONS_DIR / _PRIORITY_SVG


def eye_svg_path() -> Path:
    return _ICONS_DIR / _EYE_SVG


def plus_svg_path() -> Path:
    return _ICONS_DIR / _PLUS_SVG


def brain_svg_path() -> Path:
    return _ICONS_DIR / _BRAIN_SVG


def barred_brain_svg_path() -> Path:
    return _ICONS_DIR / _BARRED_BRAIN_SVG


def chat_svg_path() -> Path:
    return _ICONS_DIR / _CHAT_SVG


def settings_svg_path() -> Path:
    return _ICONS_DIR / _SETTINGS_SVG


def undo_svg_path() -> Path:
    return _ICONS_DIR / _UNDO_SVG


def lens_svg_path() -> Path:
    return _ICONS_DIR / _LENS_SVG


def pencil_svg_path() -> Path:
    return _ICONS_DIR / _PENCIL_SVG


def robot_svg_path() -> Path:
    return _ICONS_DIR / _ROBOT_SVG


def stop_circle_svg_path() -> Path:
    return _ICONS_DIR / _STOP_CIRCLE_SVG


def download_svg_path() -> Path:
    return _ICONS_DIR / _DOWNLOAD_SVG


def cache_svg_path() -> Path:
    return _ICONS_DIR / _CACHE_SVG


def import_svg_path() -> Path:
    return _ICONS_DIR / _IMPORT_SVG


def loading_status_icon_color() -> str:
    return get_theme_colors().msg_loading


def theme_toolbar_icon_color() -> str:
    return get_theme_colors().text_strong


def _load_svg_renderer(svg_path: Path, *, tint: str | None = None):
    if not svg_path.is_file():
        return None
    try:
        from PyQt6.QtSvg import QSvgRenderer
    except ImportError:
        return None

    from aqt.qt import QByteArray

    svg_text = svg_path.read_text(encoding="utf-8")
    if tint is not None:
        svg_text = svg_text.replace("currentColor", tint).replace("#000000", tint)
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    if not renderer.isValid():
        return None
    return renderer


def _fit_square_bounds(
    size: float,
    content_width: float,
    content_height: float,
) -> QRectF:
    if content_width <= 0 or content_height <= 0:
        return QRectF(0, 0, size, size)
    scale = min(size / content_width, size / content_height)
    width = content_width * scale
    height = content_height * scale
    x = (size - width) / 2
    y = (size - height) / 2
    return QRectF(x, y, width, height)


def render_svg_icon(
    painter: QPainter,
    bounds: QRectF,
    svg_path: Path,
    *,
    tint: str | None = None,
    rotation_degrees: float = 0,
) -> bool:
    renderer = _load_svg_renderer(svg_path, tint=tint)
    if renderer is None:
        return False

    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    if rotation_degrees:
        center = bounds.center()
        painter.translate(center.x(), center.y())
        painter.rotate(rotation_degrees)
        painter.translate(-center.x(), -center.y())
    renderer.render(painter, bounds)
    painter.restore()
    return True


def icon_from_svg(
    svg_path: Path,
    size: int,
    *,
    tint: str | None = None,
    rotation_degrees: float = 0,
) -> QIcon:
    pixmap = pixmap_from_svg(
        svg_path,
        size,
        tint=tint,
        rotation_degrees=rotation_degrees,
    )
    if pixmap.isNull():
        return QIcon()
    return QIcon(pixmap)


def pixmap_from_svg(
    svg_path: Path,
    size: int,
    *,
    tint: str | None = None,
    rotation_degrees: float = 0,
) -> QPixmap:
    renderer = _load_svg_renderer(svg_path, tint=tint)
    if renderer is None:
        return QPixmap()

    view_box = renderer.viewBoxF()
    bounds = _fit_square_bounds(size, view_box.width(), view_box.height())

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    if rotation_degrees:
        transform = QTransform()
        transform.translate(size / 2, size / 2)
        transform.rotate(rotation_degrees)
        transform.translate(-size / 2, -size / 2)
        painter.setTransform(transform)
    renderer.render(painter, bounds)
    painter.end()
    return pixmap


def stop_sign_icon(size: int | None = None) -> QIcon:
    icon_size = ICON_BUTTON_PLAIN_ICON_SIZE if size is None else size
    return icon_from_svg(stop_sign_svg_path(), icon_size, tint=None)


def priority_sign_icon(size: int | None = None) -> QIcon:
    icon_size = ICON_BUTTON_PLAIN_ICON_SIZE if size is None else size
    return icon_from_svg(priority_sign_svg_path(), icon_size, tint=None)


def themed_toolbar_icon_from_svg(svg_path: Path, size: int | None = None) -> QIcon:
    icon_size = ICON_BUTTON_PLAIN_ICON_SIZE if size is None else size
    return icon_from_svg(svg_path, icon_size, tint=theme_toolbar_icon_color())


def eye_icon(size: int | None = None) -> QIcon:
    return themed_toolbar_icon_from_svg(eye_svg_path(), size)


def plus_icon(size: int | None = None) -> QIcon:
    return themed_toolbar_icon_from_svg(plus_svg_path(), size)


def brain_icon(size: int | None = None) -> QIcon:
    icon_size = ICON_BUTTON_PLAIN_ICON_SIZE if size is None else size
    return icon_from_svg(brain_svg_path(), icon_size, tint=None)


def lens_icon(size: int | None = None) -> QIcon:
    return themed_toolbar_icon_from_svg(lens_svg_path(), size)


def pencil_icon(size: int | None = None) -> QIcon:
    return themed_toolbar_icon_from_svg(pencil_svg_path(), size)


def download_icon(size: int | None = None) -> QIcon:
    return themed_toolbar_icon_from_svg(download_svg_path(), size)


def cache_icon(size: int | None = None) -> QIcon:
    return themed_toolbar_icon_from_svg(cache_svg_path(), size)


def import_icon(size: int | None = None) -> QIcon:
    return themed_toolbar_icon_from_svg(import_svg_path(), size)


def barred_brain_icon(size: int | None = None) -> QIcon:
    icon_size = ICON_BUTTON_PLAIN_ICON_SIZE if size is None else size
    return icon_from_svg(barred_brain_svg_path(), icon_size, tint=None)


class LoadingStatusIcon(QWidget):
    """Loading-row icon; paints SVG vectors directly for crisp HiDPI rendering."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        size: int = LOADING_STATUS_ICON_SIZE,
    ) -> None:
        super().__init__(parent)
        self._svg_path: Path | None = None
        self._rotation_degrees = 0.0
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def set_loading_icon(
        self,
        svg_path: Path,
        *,
        rotation_degrees: float = 0,
    ) -> None:
        self._svg_path = svg_path
        self._rotation_degrees = rotation_degrees
        self.update()

    def paintEvent(self, _event) -> None:
        if self._svg_path is None:
            return

        renderer = _load_svg_renderer(
            self._svg_path,
            tint=loading_status_icon_color(),
        )
        if renderer is None:
            return

        painter = QPainter(self)
        side = float(min(self.width(), self.height()))
        view_box = renderer.viewBoxF()
        bounds = _fit_square_bounds(side, view_box.width(), view_box.height())

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._rotation_degrees:
            center = bounds.center()
            painter.translate(center.x(), center.y())
            painter.rotate(self._rotation_degrees)
            painter.translate(-center.x(), -center.y())
        renderer.render(painter, bounds)
        painter.restore()
        painter.end()
