from __future__ import annotations

from aqt.qt import QSplitter, Qt, QVBoxLayout, QWidget

_MIN_SECTION_HEIGHT = 56
_MIN_CHAT_HEIGHT = 120


class ChatBodySplitter(QWidget):
    """Resizable vertical stack for note preview, chat log, and edit panels."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        chat_section_index: int = -1,
    ) -> None:
        super().__init__(parent)
        self._sections: list[QWidget] = []
        self._chat_section_index = chat_section_index

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._splitter = QSplitter(Qt.Orientation.Vertical, self)
        self._splitter.setChildrenCollapsible(True)
        self._splitter.setHandleWidth(8)
        root.addWidget(self._splitter, 1)

    def splitter(self) -> QSplitter:
        return self._splitter

    def set_sections(self, *sections: QWidget) -> None:
        self._sections = list(sections)
        while self._splitter.count():
            widget = self._splitter.widget(0)
            if widget is not None:
                widget.setParent(None)
        for index, section in enumerate(self._sections):
            self._splitter.addWidget(section)
            chat_index = self._chat_section_index
            if chat_index < 0:
                chat_index = len(self._sections) - 1
            self._splitter.setStretchFactor(index, 3 if index == chat_index else 1)

    def _chat_index(self) -> int:
        if self._chat_section_index >= 0:
            return self._chat_section_index
        return len(self._sections) - 1

    def refresh_sizes(self) -> None:
        if not self._sections:
            return

        total = max(self._splitter.height(), sum(self._splitter.sizes()), 1)
        sizes = list(self._splitter.sizes())
        if len(sizes) != len(self._sections):
            sizes = [0] * len(self._sections)

        visible_indexes = [index for index, widget in enumerate(self._sections) if widget.isVisible()]
        if not visible_indexes:
            return

        if sum(size for index, size in enumerate(sizes) if self._sections[index].isVisible()) <= 0:
            sizes = self._default_sizes(total, visible_indexes)
        else:
            for index, widget in enumerate(self._sections):
                if not widget.isVisible():
                    sizes[index] = 0

        self._splitter.setSizes(sizes)

    def rebalance_on_visibility_change(self, opened_index: int | None = None) -> None:
        if not self._sections:
            return

        total = max(self._splitter.height(), sum(self._splitter.sizes()), 1)
        sizes = list(self._splitter.sizes())
        if len(sizes) != len(self._sections):
            sizes = [0] * len(self._sections)

        visible_indexes = [index for index, widget in enumerate(self._sections) if widget.isVisible()]
        if not visible_indexes:
            self._splitter.setSizes(sizes)
            return

        hidden_total = sum(
            size for index, size in enumerate(sizes) if not self._sections[index].isVisible()
        )
        if hidden_total:
            chat_index = self._chat_index()
            if chat_index in visible_indexes:
                sizes[chat_index] = max(_MIN_CHAT_HEIGHT, sizes[chat_index] + hidden_total)
            for index, widget in enumerate(self._sections):
                if not widget.isVisible():
                    sizes[index] = 0

        if opened_index is not None and self._sections[opened_index].isVisible():
            if sizes[opened_index] <= 0:
                donor = self._chat_index()
                share = max(_MIN_SECTION_HEIGHT, total // max(len(visible_indexes) + 1, 2))
                if donor in visible_indexes:
                    sizes[donor] = max(_MIN_CHAT_HEIGHT, sizes[donor] - share)
                sizes[opened_index] = share

        if sum(size for index, size in enumerate(sizes) if self._sections[index].isVisible()) <= 0:
            sizes = self._default_sizes(total, visible_indexes)

        self._splitter.setSizes(sizes)

    def _default_sizes(self, total: int, visible_indexes: list[int]) -> list[int]:
        sizes = [0] * len(self._sections)
        if not visible_indexes:
            return sizes

        chat_index = self._chat_index()
        remaining = total
        if chat_index in visible_indexes:
            chat_size = max(_MIN_CHAT_HEIGHT, int(total * 0.45))
            sizes[chat_index] = min(chat_size, remaining)
            remaining -= sizes[chat_index]
            visible_indexes = [index for index in visible_indexes if index != chat_index]

        if visible_indexes:
            each = max(_MIN_SECTION_HEIGHT, remaining // len(visible_indexes))
            for index in visible_indexes:
                sizes[index] = each

        assigned = sum(sizes)
        if assigned < total and chat_index < len(sizes):
            sizes[chat_index] += total - assigned
        return sizes
