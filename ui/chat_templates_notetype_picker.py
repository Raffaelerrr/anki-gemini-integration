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
from .card_templates import ImportedNotetypeData
from .theme import muted_hint_html
from .settings_compact_controls import create_settings_hint_label
from .themed_windows import configure_snappable_window, register_themed_window


class ChatTemplatesNotetypePicker(QDialog):
    """Pick one session-imported note type to edit templates/CSS."""

    def __init__(
        self,
        parent,
        notetypes: list[ImportedNotetypeData],
        *,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config or load_config()
        configure_snappable_window(self, application_modal=True)
        register_themed_window(self)
        self.setWindowTitle(tr("chat.edit_templates.pick.title", config=self._config))
        self.resize(420, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._intro_label = QLabel(
            tr("chat.edit_templates.pick.intro", config=self._config),
            self,
        )
        self._intro_label.setWordWrap(True)
        root.addWidget(self._intro_label)

        self._selection_hint = create_settings_hint_label(
            self,
            tr("chat.edit_templates.pick.hint", config=self._config),
        )
        root.addWidget(self._selection_hint)

        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        for data in notetypes:
            item = QListWidgetItem(data.name, self._list)
            item.setData(Qt.ItemDataRole.UserRole, data.notetype_id)
            self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
        self._list.itemDoubleClicked.connect(self.accept)
        root.addWidget(self._list, 1)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._edit_btn = buttons.addButton(
            tr("chat.edit_templates.pick.edit", config=self._config),
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self._edit_btn.setEnabled(self._list.currentItem() is not None)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        root.addWidget(buttons)

        self.apply_language()

    def apply_language(self) -> None:
        config = self._config
        self.setWindowTitle(tr("chat.edit_templates.pick.title", config=config))
        self._intro_label.setText(tr("chat.edit_templates.pick.intro", config=config))
        self._selection_hint.setText(
            muted_hint_html(tr("chat.edit_templates.pick.hint", config=config))
        )
        self._edit_btn.setText(tr("chat.edit_templates.pick.edit", config=config))

    def _on_selection_changed(self) -> None:
        self._edit_btn.setEnabled(self._list.currentItem() is not None)

    def selected_notetype_id(self) -> int | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return int(item.data(Qt.ItemDataRole.UserRole))


def pick_templates_notetype(
    parent,
    notetypes: list[ImportedNotetypeData],
    *,
    config: dict[str, Any] | None = None,
) -> int | None:
    if not notetypes:
        return None
    if len(notetypes) == 1:
        return notetypes[0].notetype_id
    dialog = ChatTemplatesNotetypePicker(parent, notetypes, config=config)
    try:
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.selected_notetype_id()
    finally:
        dialog.close()
        dialog.deleteLater()
