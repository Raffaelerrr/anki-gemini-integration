"""Pick a collection note as an APPLY_NOTE update target."""

from __future__ import annotations

from typing import Any

from aqt.qt import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    Qt,
)

from ..config import load_config
from ..i18n import tr
from ..note_apply import NoteApplyNote, rank_update_targets
from ..note_context_fields import ImportedNoteData
from .settings_compact_controls import create_settings_hint_label
from .theme import muted_hint_html
from .themed_windows import configure_snappable_window, register_themed_window


class NoteApplyCollectionPicker(QDialog):
    """Filterable list of collection notes matching the proposal's note types."""

    def __init__(
        self,
        parent,
        notes: list[ImportedNoteData],
        *,
        proposal: NoteApplyNote,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config or load_config()
        self._proposal = proposal
        self._notes = list(notes)
        configure_snappable_window(self, application_modal=True)
        register_themed_window(self)
        self.setWindowTitle(tr("chat.apply_note.collection.title", config=self._config))
        self.resize(520, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._intro_label = create_settings_hint_label(
            self,
            tr("chat.apply_note.collection.intro", config=self._config),
        )
        root.addWidget(self._intro_label)

        filter_row = QHBoxLayout()
        self._filter_label = QLabel(
            tr("chat.apply_note.collection.filter", config=self._config),
            self,
        )
        filter_row.addWidget(self._filter_label)
        self._filter_edit = QLineEdit(self)
        self._filter_edit.setClearButtonEnabled(True)
        self._filter_edit.textChanged.connect(self._rebuild_list)
        filter_row.addWidget(self._filter_edit, 1)
        root.addLayout(filter_row)

        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.itemDoubleClicked.connect(self.accept)
        root.addWidget(self._list, 1)

        self._empty_label = create_settings_hint_label(
            self,
            tr("chat.apply_note.collection.empty", config=self._config),
        )
        self._empty_label.setVisible(False)
        root.addWidget(self._empty_label)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._choose_btn = buttons.addButton(
            tr("chat.apply_note.collection.choose", config=self._config),
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        root.addWidget(buttons)

        self._rebuild_list()
        self.apply_theme()

    def selected_note_id(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None
        data = item.data(Qt.ItemDataRole.UserRole)
        return int(data) if data is not None else None

    def apply_theme(self) -> None:
        self._intro_label.setText(
            muted_hint_html(
                tr("chat.apply_note.collection.intro", config=self._config)
            )
        )
        self._empty_label.setText(
            muted_hint_html(
                tr("chat.apply_note.collection.empty", config=self._config)
            )
        )

    def _on_selection_changed(self) -> None:
        self._choose_btn.setEnabled(self._list.currentItem() is not None)

    def _rebuild_list(self, _text: str = "") -> None:
        needle = self._filter_edit.text().strip().lower()
        ranked = rank_update_targets(
            self._proposal,
            self._notes,
            source="collection",
            require_overlap=False,
        )
        self._list.clear()
        for target in ranked:
            hay = f"{target.label} {target.notetype_name} #{target.note_id}".lower()
            if needle and needle not in hay:
                continue
            suffix = (
                tr("chat.apply_note.target.suggested", config=self._config)
                if target.preferred
                else ""
            )
            label = target.label
            if target.notetype_name and target.notetype_name not in label:
                label = f"{label} ({target.notetype_name})"
            if suffix:
                label = f"{label} — {suffix}"
            item = QListWidgetItem(label, self._list)
            item.setData(Qt.ItemDataRole.UserRole, target.note_id)
            self._list.addItem(item)
        has_items = self._list.count() > 0
        self._empty_label.setVisible(not has_items)
        if has_items:
            self._list.setCurrentRow(0)
        self._on_selection_changed()


def pick_collection_note(
    parent,
    notes: list[ImportedNoteData],
    *,
    proposal: NoteApplyNote,
    config: dict[str, Any] | None = None,
) -> int | None:
    if not notes:
        return None
    dialog = NoteApplyCollectionPicker(
        parent,
        notes,
        proposal=proposal,
        config=config,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return dialog.selected_note_id()
