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

from .settings_compact_controls import create_ui_text_edit





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

        original_shell, self.original_view = create_ui_text_edit(

            self,

            editor_class=QTextEdit,

        )

        self.original_view.setReadOnly(True)

        self.original_view.setPlainText(original)

        left.addWidget(original_shell)



        right = QVBoxLayout()

        right.addWidget(QLabel(f"<b>{tr('preview.optimized', config=config)}</b>"))

        optimized_shell, self.optimized_view = create_ui_text_edit(

            self,

            editor_class=QTextEdit,

        )

        self.optimized_view.setReadOnly(True)

        self.optimized_view.setPlainText(optimized)

        right.addWidget(optimized_shell)



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
