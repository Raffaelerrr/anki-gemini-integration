from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from aqt.qt import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    Qt,
)

from ..chat_include_mask import IncludeNextMessageMask
from ..config import load_config
from ..i18n import tr
from ..note_context_fields import ImportedNoteData, ordered_imported_notes
from .card_templates import ImportedNotetypeData
from .settings_compact_controls import create_settings_hint_label
from .theme import apply_native_page_scroll_theme, refresh_native_text_edits_in
from .themed_windows import configure_snappable_window


@dataclass(frozen=True)
class IncludePanelSnapshot:
    notes: tuple[ImportedNoteData, ...]
    notetypes: tuple[ImportedNotetypeData, ...]


class _IncludeRow(QWidget):
    def __init__(
        self,
        parent: QWidget,
        *,
        title: str,
        on_changed: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self._on_changed = on_changed
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 8)
        root.setSpacing(4)
        self._title = QLabel(title, self)
        self._title.setWordWrap(True)
        root.addWidget(self._title)
        checks = QHBoxLayout()
        checks.setSpacing(12)
        self.fields_checkbox = QCheckBox(self)
        self.fields_checkbox.toggled.connect(lambda *_: self._on_changed())
        checks.addWidget(self.fields_checkbox)
        self.schema_checkbox = QCheckBox(self)
        self.schema_checkbox.toggled.connect(lambda *_: self._on_changed())
        checks.addWidget(self.schema_checkbox)
        self.templates_checkbox = QCheckBox(self)
        self.templates_checkbox.toggled.connect(lambda *_: self._on_changed())
        checks.addWidget(self.templates_checkbox)
        self.css_checkbox = QCheckBox(self)
        self.css_checkbox.toggled.connect(lambda *_: self._on_changed())
        checks.addWidget(self.css_checkbox)
        checks.addStretch(1)
        root.addLayout(checks)

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def apply_labels(self, config: dict[str, Any]) -> None:
        self.fields_checkbox.setText(tr("chat.include_panel.fields", config=config))
        self.schema_checkbox.setText(tr("chat.include_panel.schema", config=config))
        self.templates_checkbox.setText(tr("chat.include_panel.templates", config=config))
        self.css_checkbox.setText(tr("chat.include_panel.css", config=config))


class ChatIncludePanel(QWidget):
    """Choose which imported note / note-type slices go in the next message."""

    def __init__(
        self,
        parent: QWidget | None,
        *,
        on_changed: Callable[[], None],
    ) -> None:
        super().__init__(None)
        configure_snappable_window(self)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self._on_changed = on_changed
        self._mask = IncludeNextMessageMask()
        self._snapshot = IncludePanelSnapshot(notes=(), notetypes=())
        self._note_rows: dict[int, _IncludeRow] = {}
        self._notetype_rows: dict[int, _IncludeRow] = {}
        self._updating = False
        self.resize(560, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self._intro = create_settings_hint_label(self, "")
        root.addWidget(self._intro)

        actions = QHBoxLayout()
        self._select_all_btn = QPushButton(self)
        self._select_all_btn.clicked.connect(self._select_all)
        actions.addWidget(self._select_all_btn)
        self._select_none_btn = QPushButton(self)
        self._select_none_btn.clicked.connect(self._select_none)
        actions.addWidget(self._select_none_btn)
        actions.addStretch(1)
        root.addLayout(actions)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        apply_native_page_scroll_theme(scroll, allow_horizontal_scroll=False)
        self._host = QWidget(scroll)
        self._rows_layout = QVBoxLayout(self._host)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(4)
        self._rows_layout.addStretch(1)
        scroll.setWidget(self._host)
        root.addWidget(scroll, 1)

        self._empty_label = QLabel(self)
        self._empty_label.setWordWrap(True)
        root.addWidget(self._empty_label)

        footer = QHBoxLayout()
        footer.addStretch(1)
        self._close_btn = QPushButton(self)
        self._close_btn.clicked.connect(self.close)
        self._close_btn.setDefault(True)
        footer.addWidget(self._close_btn)
        root.addLayout(footer)

        self.apply_language()

    def load(
        self,
        mask: IncludeNextMessageMask,
        *,
        notes: dict[int, ImportedNoteData],
        notetypes: dict[int, ImportedNotetypeData],
    ) -> None:
        self._mask = mask
        ordered_notes = tuple(ordered_imported_notes(notes))
        ordered_types = tuple(
            sorted(notetypes.values(), key=lambda item: item.name.lower())
        )
        self._snapshot = IncludePanelSnapshot(
            notes=ordered_notes,
            notetypes=ordered_types,
        )
        self._rebuild_rows()
        self._load_checks_from_mask()
        self._refresh_empty_state()

    def apply_language(self, config: dict[str, Any] | None = None) -> None:
        config = config or load_config()
        self.setWindowTitle(tr("chat.include_panel.title", config=config))
        self._intro.setText(tr("chat.include_panel.intro", config=config))
        self._select_all_btn.setText(tr("chat.include_panel.select_all", config=config))
        self._select_none_btn.setText(tr("chat.include_panel.select_none", config=config))
        self._close_btn.setText(tr("chat.include_panel.close", config=config))
        self._empty_label.setText(tr("chat.include_panel.empty", config=config))
        for note_id, row in self._note_rows.items():
            row.apply_labels(config)
            note = next(
                (item for item in self._snapshot.notes if item.note_id == note_id),
                None,
            )
            label = note.display_label() if note is not None else str(note_id)
            row.set_title(tr("chat.include_panel.note_row", config=config, name=label))
        for notetype_id, row in self._notetype_rows.items():
            row.apply_labels(config)
            data = next(
                (item for item in self._snapshot.notetypes if item.notetype_id == notetype_id),
                None,
            )
            name = data.name if data is not None else str(notetype_id)
            row.set_title(tr("chat.include_panel.notetype_row", config=config, name=name))

    def apply_theme(self) -> None:
        refresh_native_text_edits_in(self)

    def _rebuild_rows(self) -> None:
        while self._rows_layout.count():
            item = self._rows_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        self._note_rows = {}
        self._notetype_rows = {}
        config = load_config()

        for note in self._snapshot.notes:
            row = _IncludeRow(
                self._host,
                title=tr(
                    "chat.include_panel.note_row",
                    config=config,
                    name=note.display_label(),
                ),
                on_changed=self._on_row_changed,
            )
            row.apply_labels(config)
            row.schema_checkbox.setVisible(False)
            row.templates_checkbox.setVisible(False)
            row.css_checkbox.setVisible(False)
            self._note_rows[note.note_id] = row
            self._rows_layout.addWidget(row)

        for data in self._snapshot.notetypes:
            row = _IncludeRow(
                self._host,
                title=tr(
                    "chat.include_panel.notetype_row",
                    config=config,
                    name=data.name,
                ),
                on_changed=self._on_row_changed,
            )
            row.apply_labels(config)
            row.fields_checkbox.setVisible(False)
            self._notetype_rows[data.notetype_id] = row
            self._rows_layout.addWidget(row)

        self._rows_layout.addStretch(1)

    def _load_checks_from_mask(self) -> None:
        self._updating = True
        try:
            for note in self._snapshot.notes:
                row = self._note_rows.get(note.note_id)
                if row is None:
                    continue
                row.fields_checkbox.setEnabled(True)
                row.fields_checkbox.setChecked(
                    bool(self._mask.note_fields.get(note.note_id, False))
                )

            for data in self._snapshot.notetypes:
                row = self._notetype_rows.get(data.notetype_id)
                if row is None:
                    continue
                has_templates = bool(data.templates)
                has_css = bool(data.css.strip())
                row.schema_checkbox.setEnabled(True)
                row.schema_checkbox.setChecked(
                    bool(self._mask.schemas.get(data.notetype_id, False))
                )
                row.templates_checkbox.setEnabled(has_templates)
                row.templates_checkbox.setChecked(
                    bool(self._mask.templates.get(data.notetype_id, False)) and has_templates
                )
                row.css_checkbox.setEnabled(has_css)
                row.css_checkbox.setChecked(
                    bool(self._mask.css.get(data.notetype_id, False)) and has_css
                )
        finally:
            self._updating = False

    def _refresh_empty_state(self) -> None:
        has_rows = bool(self._note_rows) or bool(self._notetype_rows)
        self._empty_label.setVisible(not has_rows)
        self._select_all_btn.setEnabled(has_rows)
        self._select_none_btn.setEnabled(has_rows)

    def _on_row_changed(self) -> None:
        if self._updating:
            return
        self._write_mask_from_rows()
        self._on_changed()

    def _write_mask_from_rows(self) -> None:
        for note_id, row in self._note_rows.items():
            self._mask.ensure_note(note_id)
            self._mask.note_fields[note_id] = row.fields_checkbox.isChecked()
        for notetype_id, row in self._notetype_rows.items():
            self._mask.ensure_notetype(notetype_id)
            self._mask.schemas[notetype_id] = row.schema_checkbox.isChecked()
            self._mask.templates[notetype_id] = row.templates_checkbox.isChecked()
            self._mask.css[notetype_id] = row.css_checkbox.isChecked()

    def _select_all(self) -> None:
        self._updating = True
        try:
            for row in self._note_rows.values():
                if row.fields_checkbox.isEnabled():
                    row.fields_checkbox.setChecked(True)
            for row in self._notetype_rows.values():
                if row.schema_checkbox.isEnabled():
                    row.schema_checkbox.setChecked(True)
                if row.templates_checkbox.isEnabled():
                    row.templates_checkbox.setChecked(True)
                if row.css_checkbox.isEnabled():
                    row.css_checkbox.setChecked(True)
        finally:
            self._updating = False
        self._write_mask_from_rows()
        self._on_changed()

    def _select_none(self) -> None:
        self._updating = True
        try:
            for row in self._note_rows.values():
                row.fields_checkbox.setChecked(False)
            for row in self._notetype_rows.values():
                row.schema_checkbox.setChecked(False)
                row.templates_checkbox.setChecked(False)
                row.css_checkbox.setChecked(False)
        finally:
            self._updating = False
        self._write_mask_from_rows()
        self._on_changed()
