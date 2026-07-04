"""Native Qt control factories — single entry point for addon UI widgets."""

from __future__ import annotations

from typing import TypeVar

from aqt.qt import QComboBox, QDoubleSpinBox, QLineEdit, QSpinBox, QTextEdit, QWidget

from .theme import apply_native_text_edit_surface_theme
from .widgets import (
    PlainNoWheelComboBox,
    PlainNoWheelDoubleSpinBox,
    PlainNoWheelSpinBox,
    ScrollAwareTextEdit,
)

_TEditor = TypeVar("_TEditor", bound=QTextEdit)


def create_ui_line_edit(parent: QWidget) -> tuple[QWidget, QLineEdit]:
    editor = QLineEdit(parent)
    return editor, editor


def create_ui_text_edit(
    parent: QWidget,
    *,
    editor_class: type[_TEditor] = ScrollAwareTextEdit,
) -> tuple[QWidget, _TEditor]:
    editor = editor_class(parent)
    apply_native_text_edit_surface_theme(editor)
    return editor, editor


def create_settings_line_edit(parent: QWidget) -> tuple[QWidget, QLineEdit]:
    return create_ui_line_edit(parent)


def create_settings_text_edit(
    parent: QWidget,
    *,
    editor_class: type[_TEditor] = ScrollAwareTextEdit,
) -> tuple[QWidget, _TEditor]:
    return create_ui_text_edit(parent, editor_class=editor_class)


def create_settings_spinbox(parent: QWidget) -> tuple[QWidget, QSpinBox]:
    control = PlainNoWheelSpinBox(parent)
    return control, control


def create_settings_double_spinbox(parent: QWidget) -> tuple[QWidget, QDoubleSpinBox]:
    control = PlainNoWheelDoubleSpinBox(parent)
    return control, control


def create_settings_combo(parent: QWidget) -> tuple[QWidget, QComboBox]:
    control = PlainNoWheelComboBox(parent)
    return control, control


def create_settings_model_selector_shell(parent: QWidget) -> tuple[QWidget, QComboBox]:
    control = PlainNoWheelComboBox(parent)
    return control, control
