from __future__ import annotations

import time
from typing import Any

from aqt.qt import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ..config import api_key_configured
from ..i18n import tr
from ..prompt_cache import (
    PromptCacheError,
    RemotePromptCacheEntry,
    delete_remote_prompt_cache,
    delete_untracked_addon_caches,
    list_addon_remote_caches,
)
from .prompt_cache_confirm import confirm_delete_orphan_caches
from .themed_windows import configure_snappable_window, register_themed_window


class PromptCacheManagerDialog(QDialog):
    def __init__(self, parent: QWidget | None, *, config: dict[str, Any]) -> None:
        super().__init__(parent)
        self.config = config
        self._entries: list[RemotePromptCacheEntry] = []
        configure_snappable_window(self, application_modal=True)
        self.setWindowTitle(tr("settings.prompt_cache.manager.title", config=config))
        self.resize(720, 360)

        root = QVBoxLayout(self)
        self._status_label = QLabel(self)
        self._status_label.setWordWrap(True)
        root.addWidget(self._status_label)

        self._intro_label = QLabel(self)
        self._intro_label.setWordWrap(True)
        self._intro_label.setTextFormat(Qt.TextFormat.RichText)
        self._intro_label.setText(tr("settings.prompt_cache.manager.intro", config=config))
        root.addWidget(self._intro_label)

        self._table = QTableWidget(0, 5, self)
        self._table.setHorizontalHeaderLabels(
            [
                tr("settings.prompt_cache.manager.col.purpose", config=config),
                tr("settings.prompt_cache.manager.col.model", config=config),
                tr("settings.prompt_cache.manager.col.expires", config=config),
                tr("settings.prompt_cache.manager.col.tracked", config=config),
                tr("settings.prompt_cache.manager.col.actions", config=config),
            ]
        )
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table, 1)

        btn_row = QHBoxLayout()
        self._refresh_btn = QPushButton(
            tr("settings.prompt_cache.manager.refresh", config=config),
            self,
        )
        self._refresh_btn.clicked.connect(self._refresh)
        self._delete_orphans_btn = QPushButton(
            tr("settings.prompt_cache.manager.delete_orphans", config=config),
            self,
        )
        self._delete_orphans_btn.clicked.connect(self._delete_orphans)
        self._close_btn = QPushButton(tr("settings.prompt_cache.manager.close", config=config), self)
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._refresh_btn)
        btn_row.addWidget(self._delete_orphans_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self._close_btn)
        root.addLayout(btn_row)

        self._refresh()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        register_themed_window(self)

    def _purpose_label(self, purpose: str | None) -> str:
        if purpose == "chat":
            return tr("settings.prompt_cache.manager.purpose.chat", config=self.config)
        if purpose == "optimize":
            return tr("settings.prompt_cache.manager.purpose.optimize", config=self.config)
        return tr("settings.prompt_cache.manager.purpose.unknown", config=self.config)

    def _expires_label(self, expire_at: float) -> str:
        remaining = int(expire_at - time.time())
        if remaining <= 0:
            return tr("settings.prompt_cache.manager.expired", config=self.config)
        minutes = max(1, remaining // 60)
        return tr("settings.prompt_cache.manager.minutes", config=self.config, minutes=minutes)

    def _refresh(self) -> None:
        self._table.setRowCount(0)
        self._entries = []
        if not api_key_configured(self.config):
            self._status_label.setText(
                tr("settings.prompt_cache.manager.no_api_key", config=self.config)
            )
            self._delete_orphans_btn.setEnabled(False)
            return
        try:
            self._entries = list_addon_remote_caches(self.config)
        except PromptCacheError as exc:
            self._status_label.setText(
                tr(
                    "settings.prompt_cache.manager.load_error",
                    config=self.config,
                    error=str(exc)[:200],
                )
            )
            self._delete_orphans_btn.setEnabled(False)
            return

        if not self._entries:
            self._status_label.setText(
                tr("settings.prompt_cache.manager.empty", config=self.config)
            )
            self._delete_orphans_btn.setEnabled(False)
            return

        orphan_count = sum(1 for entry in self._entries if not entry.tracked)
        self._status_label.setText(
            tr(
                "settings.prompt_cache.manager.summary",
                config=self.config,
                count=len(self._entries),
                orphans=orphan_count,
            )
        )
        self._delete_orphans_btn.setEnabled(orphan_count > 0)

        for row, entry in enumerate(self._entries):
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(self._purpose_label(entry.purpose)))
            self._table.setItem(row, 1, QTableWidgetItem(entry.model or "—"))
            self._table.setItem(row, 2, QTableWidgetItem(self._expires_label(entry.expire_at)))
            tracked = tr(
                "settings.prompt_cache.manager.tracked_yes"
                if entry.tracked
                else "settings.prompt_cache.manager.tracked_no",
                config=self.config,
            )
            self._table.setItem(row, 3, QTableWidgetItem(tracked))

            delete_btn = QPushButton(
                tr("settings.prompt_cache.manager.delete", config=self.config),
                self._table,
            )
            delete_btn.clicked.connect(
                lambda _checked=False, name=entry.name, purpose=entry.purpose: self._delete_one(
                    name,
                    purpose,
                )
            )
            self._table.setCellWidget(row, 4, delete_btn)

    def _delete_one(self, cache_name: str, purpose: str | None) -> None:
        purpose_arg = purpose if purpose in ("chat", "optimize") else None
        delete_remote_prompt_cache(
            self.config,
            cache_name,
            purpose=purpose_arg,
        )
        self._refresh()

    def _delete_orphans(self) -> None:
        if not self._entries:
            return
        orphans = [entry for entry in self._entries if not entry.tracked]
        if not orphans:
            return
        if not confirm_delete_orphan_caches(
            self,
            self.config,
            count=len(orphans),
        ):
            return
        delete_untracked_addon_caches(self.config)
        self._refresh()

    def apply_theme(self) -> None:
        config = self.config
        self.setWindowTitle(tr("settings.prompt_cache.manager.title", config=config))
        self._intro_label.setText(tr("settings.prompt_cache.manager.intro", config=config))
        self._table.setHorizontalHeaderLabels(
            [
                tr("settings.prompt_cache.manager.col.purpose", config=config),
                tr("settings.prompt_cache.manager.col.model", config=config),
                tr("settings.prompt_cache.manager.col.expires", config=config),
                tr("settings.prompt_cache.manager.col.tracked", config=config),
                tr("settings.prompt_cache.manager.col.actions", config=config),
            ]
        )
        self._refresh_btn.setText(tr("settings.prompt_cache.manager.refresh", config=config))
        self._delete_orphans_btn.setText(
            tr("settings.prompt_cache.manager.delete_orphans", config=config)
        )
        self._close_btn.setText(tr("settings.prompt_cache.manager.close", config=config))


def open_prompt_cache_manager(parent: QWidget | None, *, config: dict[str, Any]) -> None:
    dialog = PromptCacheManagerDialog(parent, config=config)
    dialog.exec()
