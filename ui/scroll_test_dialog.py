from __future__ import annotations

from typing import Callable

from aqt.qt import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    Qt,
    QVBoxLayout,
    QWidget,
)

from .theme import apply_native_text_edit_surface_theme
from .widgets import ScrollAwareTextEdit, _wheel_deltas

WheelLogFn = Callable[[str], None]
_MAX_LOG_LINES = 200


def _sample_scroll_content() -> str:
    lines: list[str] = []
    for index in range(40):
        tabs = "\t" * (4 + index % 8)
        lines.append(f"{tabs}Line {index + 1:02d}: " + "scroll-test " * 18)
    return "\n".join(lines)


def _phase_label(event) -> str:
    phase = event.phase()
    names = {
        Qt.ScrollPhase.NoScrollPhase: "none",
        Qt.ScrollPhase.ScrollBegin: "begin",
        Qt.ScrollPhase.ScrollUpdate: "update",
        Qt.ScrollPhase.ScrollEnd: "end",
    }
    if phase in names:
        return names[phase]
    enum_name = getattr(phase, "name", "")
    if enum_name:
        return enum_name.removeprefix("ScrollPhase.")
    return str(phase)


def _format_wheel_line(
    *,
    source: str,
    event,
    consumed: bool | None,
    v_before: int,
    h_before: int,
    v_after: int,
    h_after: int,
) -> str:
    pixel = event.pixelDelta()
    angle = event.angleDelta()
    delta_y, delta_x = _wheel_deltas(event)
    both = delta_x != 0 and delta_y != 0
    axis = "both" if both else ("v" if delta_y != 0 else ("h" if delta_x != 0 else "none"))
    if consumed is None:
        path = "native"
    elif consumed:
        path = "intercepted"
    else:
        path = "pass-through"
    line = (
        f"[{source}] path={path} axis={axis} "
        f"ang=({angle.x()},{angle.y()}) used=({delta_x},{delta_y}) "
        f"px=({pixel.x()},{pixel.y()}) phase={_phase_label(event)} "
        f"v={v_before} h={h_before}"
    )
    if v_after != v_before or h_after != h_before:
        line += f" -> v={v_after} h={h_after}"
    return line


class _LoggedPlainTextEdit(QTextEdit):
    """Plain QTextEdit that logs each wheelEvent after native scroll handling."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        log_line: WheelLogFn,
        logging_enabled: Callable[[], bool],
    ) -> None:
        super().__init__(parent)
        self._wheel_log_line = log_line
        self._wheel_logging_enabled = logging_enabled

    def wheelEvent(self, event) -> None:
        vbar = self.verticalScrollBar()
        hbar = self.horizontalScrollBar()
        v_before = vbar.value()
        h_before = hbar.value()
        super().wheelEvent(event)
        if not self._wheel_logging_enabled():
            return
        self._wheel_log_line(
            _format_wheel_line(
                source="plain",
                event=event,
                consumed=None,
                v_before=v_before,
                h_before=h_before,
                v_after=vbar.value(),
                h_after=hbar.value(),
            )
        )


class _LoggedScrollAwareTextEdit(ScrollAwareTextEdit):
    """ScrollAwareTextEdit that logs each wheelEvent after routing + scroll."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        log_line: WheelLogFn,
        logging_enabled: Callable[[], bool],
    ) -> None:
        super().__init__(parent)
        self._wheel_log_line = log_line
        self._wheel_logging_enabled = logging_enabled

    def wheelEvent(self, event) -> None:
        vbar = self.verticalScrollBar()
        hbar = self.horizontalScrollBar()
        v_before = vbar.value()
        h_before = hbar.value()
        consumed = ScrollAwareTextEdit._would_intercept_wheel(self, event)
        super().wheelEvent(event)
        if not self._wheel_logging_enabled():
            return
        self._wheel_log_line(
            _format_wheel_line(
                source="scroll-aware",
                event=event,
                consumed=consumed,
                v_before=v_before,
                h_before=h_before,
                v_after=vbar.value(),
                h_after=hbar.value(),
            )
        )


class ScrollTestDialog(QDialog):
    """A/B scroll test: plain QTextEdit vs ScrollAwareTextEdit with wheel logging."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Scroll test (debug)")
        self.resize(980, 720)
        self._logging_enabled = True

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "<b>How to use</b><br>"
                "1. Click the left or right box to focus it.<br>"
                "2. Reset sample text so both scrollbars start centered.<br>"
                "3. Two-finger diagonal scroll (~45°). Compare plain Qt (left) vs ScrollAware (right).<br>"
                "4. On Windows, <code>px=(0,0)</code> is normal — read <code>ang=</code> and <code>used=</code>.<br>"
                "5. Windows usually sends <b>one axis per event</b> (<code>axis=v</code> then <code>axis=h</code>), "
                "not <code>axis=both</code>. Long runs of a single axis during a diagonal gesture are expected "
                "and affect plain Qt too.<br>"
                "6. Left logs <code>path=native</code>; right logs <code>pass-through</code> or "
                "<code>intercepted</code>. Trailing <code>-&gt; v=… h=…</code> is movement from that event only."
            )
        )

        columns = QHBoxLayout()
        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("<b>Plain QTextEdit</b> (no addon wheel routing)"))
        self._plain_editor = _LoggedPlainTextEdit(
            self,
            log_line=self._append_log,
            logging_enabled=self._is_logging_enabled,
        )
        self._configure_test_editor(self._plain_editor)
        left_col.addWidget(self._plain_editor)

        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("<b>ScrollAwareTextEdit</b> (addon behavior)"))
        self._aware_editor = _LoggedScrollAwareTextEdit(
            self,
            log_line=self._append_log,
            logging_enabled=self._is_logging_enabled,
        )
        self._configure_test_editor(self._aware_editor)
        right_col.addWidget(self._aware_editor)

        columns.addLayout(left_col, 1)
        columns.addLayout(right_col, 1)
        root.addLayout(columns, 1)

        controls = QHBoxLayout()
        self._log_checkbox = QCheckBox("Log wheel events", self)
        self._log_checkbox.setChecked(True)
        self._log_checkbox.toggled.connect(self._on_log_toggled)
        controls.addWidget(self._log_checkbox)
        reset_button = QPushButton("Reset sample text", self)
        reset_button.clicked.connect(self._reset_sample_text)
        clear_button = QPushButton("Clear log", self)
        clear_button.clicked.connect(self._clear_log)
        controls.addWidget(reset_button)
        controls.addWidget(clear_button)
        controls.addStretch(1)
        root.addLayout(controls)

        self._log_view = QPlainTextEdit(self)
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(_MAX_LOG_LINES)
        self._log_view.setPlaceholderText("Wheel events appear here…")
        root.addWidget(self._log_view, 1)

        self._reset_sample_text()
        self._append_log("Ready. Focus a box and scroll.")

    def _configure_test_editor(self, editor: QTextEdit) -> None:
        apply_native_text_edit_surface_theme(editor)
        editor.setFixedHeight(220)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def _is_logging_enabled(self) -> bool:
        return self._logging_enabled

    def _on_log_toggled(self, checked: bool) -> None:
        self._logging_enabled = checked

    def _reset_sample_text(self) -> None:
        sample = _sample_scroll_content()
        self._plain_editor.setPlainText(sample)
        self._aware_editor.setPlainText(sample)
        for editor in (self._plain_editor, self._aware_editor):
            vbar = editor.verticalScrollBar()
            hbar = editor.horizontalScrollBar()
            vbar.setValue((vbar.minimum() + vbar.maximum()) // 2)
            hbar.setValue((hbar.minimum() + hbar.maximum()) // 2)
        self._append_log("Sample text loaded; scrollbars centered.")

    def _clear_log(self) -> None:
        self._log_view.clear()

    def _append_log(self, line: str) -> None:
        if not self._logging_enabled:
            return
        self._log_view.appendPlainText(line)


_scroll_test_dialog: ScrollTestDialog | None = None


def _clear_scroll_test_dialog_ref(_result: int | None = None) -> None:
    global _scroll_test_dialog
    _scroll_test_dialog = None


def open_scroll_test_dialog(parent: QWidget | None = None) -> ScrollTestDialog:
    global _scroll_test_dialog
    if _scroll_test_dialog is not None:
        try:
            if _scroll_test_dialog.isVisible():
                _scroll_test_dialog.raise_()
                _scroll_test_dialog.activateWindow()
                return _scroll_test_dialog
        except RuntimeError:
            _scroll_test_dialog = None
        else:
            _scroll_test_dialog = None
    dialog = ScrollTestDialog(parent)
    _scroll_test_dialog = dialog
    dialog.finished.connect(_clear_scroll_test_dialog_ref)
    dialog.show()
    return dialog
