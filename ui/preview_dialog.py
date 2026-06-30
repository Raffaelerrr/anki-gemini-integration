from __future__ import annotations

from aqt.qt import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class PreviewDialog(QDialog):
    def __init__(self, parent, original: str, optimized: str):
        super().__init__(parent)
        self.setWindowTitle("Anteprima ottimizzazione Gemini")
        self.resize(900, 550)
        layout = QVBoxLayout(self)

        layout.addWidget(
            QLabel(
                "<b>Confronta il contenuto originale con la versione ottimizzata.</b> "
                "Clicca <i>Applica</i> per sostituire il campo, oppure <i>Annulla</i> per mantenere l'originale."
            )
        )

        columns = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Originale</b>"))
        self.original_view = QTextEdit(self)
        self.original_view.setReadOnly(True)
        self.original_view.setPlainText(original)
        left.addWidget(self.original_view)

        right = QVBoxLayout()
        right.addWidget(QLabel("<b>Ottimizzato</b>"))
        self.optimized_view = QTextEdit(self)
        self.optimized_view.setReadOnly(True)
        self.optimized_view.setPlainText(optimized)
        right.addWidget(self.optimized_view)

        columns.addLayout(left)
        columns.addLayout(right)
        layout.addLayout(columns)

        btn_row = QHBoxLayout()
        btn_apply = QPushButton("Applica", self)
        btn_apply.clicked.connect(self.accept)
        btn_cancel = QPushButton("Annulla", self)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_apply)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)
