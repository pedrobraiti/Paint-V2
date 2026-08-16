"""Barra lateral de ferramentas, agrupada por finalidade.

Os pincéis de efeito ficam num grupo próprio, separado dos de desenho: são eles
que o Paint original não tem, e agrupá-los deixa isso explícito em vez de diluí-los
no meio do lápis e da borracha.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...tools.base import Tool
from ...tools.registry import grouped_tool_classes
from ..icons import get_icon

COLUMNS = 2
BUTTON_SIZE = 40
ICON_SIZE = 20


class ToolBox(QWidget):
    """Grade de botões que seleciona a ferramenta ativa."""

    tool_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: dict[str, QToolButton] = {}
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        for title, tool_classes in grouped_tool_classes():
            layout.addWidget(self._build_group(title, tool_classes))
        layout.addStretch(1)

    def _build_group(self, title: str, tool_classes: list[type[Tool]]) -> QWidget:
        container = QWidget()
        box = QVBoxLayout(container)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(5)

        label = QLabel(title)
        label.setProperty("role", "section")
        box.addWidget(label)

        grid = QGridLayout()
        grid.setSpacing(5)
        for index, tool_class in enumerate(tool_classes):
            button = self._build_button(tool_class)
            grid.addWidget(button, index // COLUMNS, index % COLUMNS)
        box.addLayout(grid)
        return container

    def _build_button(self, tool_class: type[Tool]) -> QToolButton:
        button = QToolButton()
        button.setCheckable(True)
        button.setAutoRaise(True)
        button.setIcon(get_icon(tool_class.icon, ICON_SIZE))
        button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
        button.setFixedSize(BUTTON_SIZE, BUTTON_SIZE)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(_tooltip(tool_class))
        button.clicked.connect(lambda _, key=tool_class.key: self.tool_selected.emit(key))

        self._group.addButton(button)
        self._buttons[tool_class.key] = button
        return button

    def set_active(self, key: str) -> None:
        button = self._buttons.get(key)
        if button is not None and not button.isChecked():
            button.setChecked(True)


def _tooltip(tool_class: type[Tool]) -> str:
    shortcut = f"  ({tool_class.shortcut})" if tool_class.shortcut else ""
    return f"<b>{tool_class.label}</b>{shortcut}<br>{tool_class.hint}"
