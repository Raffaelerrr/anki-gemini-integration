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



from ..config import load_config
from ..i18n import tr

from .settings_compact_controls import create_ui_text_edit
from .theme import refresh_native_text_edits_in
from .themed_windows import configure_snappable_window, register_themed_window





class PreviewDialog(QDialog):

    def __init__(self, parent, original: str, optimized: str, *, config: dict[str, Any] | None = None):

        super().__init__(parent)

        self._config = config

        configure_snappable_window(self, application_modal=True)
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

        self._intro_label = layout.itemAt(0).widget()
        self._original_label = left.itemAt(0).widget()
        self._optimized_label = right.itemAt(0).widget()
        self._btn_apply = btn_apply
        self._btn_cancel = btn_cancel

        register_themed_window(self)

    def apply_theme(self) -> None:
        config = load_config()
        self.setWindowTitle(tr("preview.title", config=config))
        self._intro_label.setText(tr("preview.intro", config=config))
        self._original_label.setText(f"<b>{tr('preview.original', config=config)}</b>")
        self._optimized_label.setText(f"<b>{tr('preview.optimized', config=config)}</b>")
        self._btn_apply.setText(tr("preview.apply", config=config))
        self._btn_cancel.setText(tr("preview.cancel", config=config))
        refresh_native_text_edits_in(self)
