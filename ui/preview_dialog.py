from __future__ import annotations

from typing import Any

from aqt.qt import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..i18n import tr


class PreviewDialog(QDialog):
    def __init__(self, parent, original: str, optimized: str, *, config: dict[str, Any] | None = None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle(tr("preview.title", config=config))
        self.resize(900, 550)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(tr("preview.intro", config=config)))

        columns = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel(f"<b>{tr('preview.original', config=config)}</b>"))
        self.original_view = QTextEdit(self)
        self.original_view.setReadOnly(True)
        self.original_view.setPlainText(original)
        left.addWidget(self.original_view)

        right = QVBoxLayout()
        right.addWidget(QLabel(f"<b>{tr('preview.optimized', config=config)}</b>"))
        self.optimized_view = QTextEdit(self)
        self.optimized_view.setReadOnly(True)
        self.optimized_view.setPlainText(optimized)
        right.addWidget(self.optimized_view)

        columns.addLayout(left)
        columns.addLayout(right)
        layout.addLayout(columns)

        btn_row = QHBoxLayout()
        btn_apply = QPushButton(tr("preview.apply", config=config), self)
        btn_apply.clicked.connect(self.accept)
        btn_cancel = QPushButton(tr("preview.cancel", config=config), self)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_apply)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)
