from __future__ import annotations

from typing import Any

from aqt.qt import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    Qt,
)

from ..config import load_config
from ..i18n import tr
from ..note_context_fields import ImportedNoteData, ordered_imported_notes
from .theme import muted_hint_html
from .settings_compact_controls import create_settings_hint_label
from .themed_windows import configure_snappable_window, register_themed_window


class ChatImportedNotePicker(QDialog):
    """Pick one session-imported note for edit or preview."""

    def __init__(
        self,
        parent,
        notes: list[ImportedNoteData],
        *,
        config: dict[str, Any] | None = None,
        purpose: str = "edit",
    ) -> None:
        super().__init__(parent)
        self._config = config or load_config()
        self._purpose = purpose if purpose in {"edit", "preview"} else "edit"
        configure_snappable_window(self, application_modal=True)
        register_themed_window(self)
        self.setWindowTitle(self._title_text())
        self.resize(460, 380)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._intro_label = QLabel(self._intro_text(), self)
        self._intro_label.setWordWrap(True)
        root.addWidget(self._intro_label)

        self._selection_hint = create_settings_hint_label(
            self,
            tr("chat.imported_note.pick.hint", config=self._config),
        )
        root.addWidget(self._selection_hint)

        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for note in notes:
            item = QListWidgetItem(note.display_label(), self._list)
            item.setData(Qt.ItemDataRole.UserRole, note.note_id)
            self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
        self._list.itemDoubleClicked.connect(self.accept)
        root.addWidget(self._list, 1)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._action_btn = buttons.addButton(
            self._action_text(),
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self._action_btn.setEnabled(self._list.currentItem() is not None)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        root.addWidget(buttons)

        self.apply_language()

    def _title_text(self) -> str:
        key = (
            "chat.imported_note.pick.title.preview"
            if self._purpose == "preview"
            else "chat.imported_note.pick.title.edit"
        )
        return tr(key, config=self._config)

    def _intro_text(self) -> str:
        key = (
            "chat.imported_note.pick.intro.preview"
            if self._purpose == "preview"
            else "chat.imported_note.pick.intro.edit"
        )
        return tr(key, config=self._config)

    def _action_text(self) -> str:
        key = (
            "chat.imported_note.pick.preview"
            if self._purpose == "preview"
            else "chat.imported_note.pick.edit"
        )
        return tr(key, config=self._config)

    def apply_language(self) -> None:
        self.setWindowTitle(self._title_text())
        self._intro_label.setText(self._intro_text())
        self._selection_hint.setText(
            muted_hint_html(tr("chat.imported_note.pick.hint", config=self._config))
        )
        self._action_btn.setText(self._action_text())

    def _on_selection_changed(self) -> None:
        self._action_btn.setEnabled(self._list.currentItem() is not None)

    def selected_note_id(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))


def pick_imported_note(
    parent,
    notes: dict[int, ImportedNoteData] | list[ImportedNoteData],
    *,
    config: dict[str, Any] | None = None,
    purpose: str = "edit",
) -> int | None:
    if isinstance(notes, dict):
        ordered = ordered_imported_notes(notes)
    else:
        ordered = list(notes)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0].note_id
    dialog = ChatImportedNotePicker(
        parent,
        ordered,
        config=config,
        purpose=purpose,
    )
    try:
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.selected_note_id()
    finally:
        dialog.close()
        dialog.deleteLater()
