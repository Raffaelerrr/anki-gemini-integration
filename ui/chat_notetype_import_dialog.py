from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aqt import mw
from aqt.qt import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    Qt,
)

from ..config import load_config, save_config
from ..i18n import tr
from .theme import muted_hint_html
from .settings_compact_controls import create_settings_hint_label
from .themed_windows import configure_snappable_window, register_themed_window


@dataclass(frozen=True)
class NotetypeImportSelection:
    notetype_ids: tuple[int, ...]
    include_templates: bool
    include_css: bool


class ChatNotetypeImportDialog(QDialog):
    def __init__(self, parent, *, config: dict[str, Any] | None = None) -> None:
        super().__init__(parent)
        self._config = config or load_config()
        configure_snappable_window(self, application_modal=True)
        register_themed_window(self)
        self.setWindowTitle(tr("chat.import_notetype.title", config=self._config))
        self.resize(520, 420)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        intro = QLabel(tr("chat.import_notetype.intro", config=self._config), self)
        intro.setWordWrap(True)
        self._intro_label = intro
        root.addWidget(intro)

        self._selection_hint = create_settings_hint_label(
            self,
            tr("chat.import_notetype.selection_hint", config=self._config),
        )
        root.addWidget(self._selection_hint)

        self._list = QListWidget(self)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for model in sorted(mw.col.models.all(), key=lambda item: str(item.get("name") or "").lower()):
            notetype_id = int(model.get("id") or 0)
            name = str(model.get("name") or "").strip() or tr(
                "common.note_type_fallback",
                config=self._config,
                id=notetype_id,
            )
            item = QListWidgetItem(name, self._list)
            item.setData(Qt.ItemDataRole.UserRole, notetype_id)
            self._list.addItem(item)
        root.addWidget(self._list, 1)

        options_row = QHBoxLayout()
        self._include_templates_checkbox = QCheckBox(self)
        self._include_templates_checkbox.setChecked(
            bool(self._config.get("brain_import_templates", False))
        )
        options_row.addWidget(self._include_templates_checkbox)
        self._include_css_checkbox = QCheckBox(self)
        self._include_css_checkbox.setChecked(bool(self._config.get("brain_import_css", False)))
        options_row.addWidget(self._include_css_checkbox)
        options_row.addStretch(1)
        root.addLayout(options_row)

        buttons = QDialogButtonBox(self)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._import_btn = buttons.addButton(
            tr("chat.import_notetype.import_button", config=self._config),
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self._import_btn.setEnabled(False)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        root.addWidget(buttons)

        self.apply_language()

    def apply_language(self) -> None:
        config = self._config
        self.setWindowTitle(tr("chat.import_notetype.title", config=config))
        self._intro_label.setText(tr("chat.import_notetype.intro", config=config))
        self._selection_hint.setText(
            muted_hint_html(tr("chat.import_notetype.selection_hint", config=config))
        )
        self._include_templates_checkbox.setText(
            tr("settings.brain_import_templates", config=config)
        )
        self._include_css_checkbox.setText(tr("settings.brain_import_css", config=config))
        self._import_btn.setText(tr("chat.import_notetype.import_button", config=config))

    def _on_selection_changed(self) -> None:
        self._import_btn.setEnabled(bool(self._list.selectedItems()))

    def selection(self) -> NotetypeImportSelection | None:
        selected_ids = [
            int(item.data(Qt.ItemDataRole.UserRole))
            for item in self._list.selectedItems()
        ]
        if not selected_ids:
            return None
        return NotetypeImportSelection(
            notetype_ids=tuple(sorted(set(selected_ids))),
            include_templates=self._include_templates_checkbox.isChecked(),
            include_css=self._include_css_checkbox.isChecked(),
        )


def confirm_notetype_import(parent, *, config: dict[str, Any] | None = None) -> NotetypeImportSelection | None:
    dialog = ChatNotetypeImportDialog(parent, config=config)
    try:
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        selection = dialog.selection()
        if selection is None:
            return None
        merged_config = load_config()
        merged_config["brain_import_templates"] = selection.include_templates
        merged_config["brain_import_css"] = selection.include_css
        save_config(merged_config)
        return selection
    finally:
        dialog.close()
        dialog.deleteLater()
