"""Painel de cores: par ativo, paleta fixa e cores recentes.

O par primário/secundário aparece empilhado, como nos editores clássicos, porque
essa é a metáfora que o botão direito do mouse usa: esquerdo pinta com a de cima,
direito com a de baixo.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QColorDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...tools.settings import ToolSettings
from ..theme import PALETTE

SWATCH_SIZE = 22
PALETTE_COLUMNS = 10

STANDARD_COLORS = (
    "#000000", "#7F7F7F", "#880015", "#ED1C24", "#FF7F27",
    "#FFF200", "#22B14C", "#00A2E8", "#3F48CC", "#A349A4",
    "#FFFFFF", "#C3C3C3", "#B97A57", "#FFAEC9", "#FFC90E",
    "#EFE4B0", "#B5E61D", "#99D9EA", "#7092BE", "#C8BFE7",
    "#14161B", "#242832", "#454C5D", "#98A0B2", "#E7E9EF",
    "#FF9F45", "#FF6B6B", "#4CC2FF", "#4ADE80", "#C084FC",
)


def _checkerboard(painter: QPainter, rect: QRectF) -> None:
    """Fundo xadrez sob cores com transparência."""
    painter.fillRect(rect, QColor(PALETTE.checker_dark))
    step = rect.height() / 4.0
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(PALETTE.checker_light))
    for row in range(4):
        for column in range(4):
            if (row + column) % 2:
                continue
            painter.drawRect(
                QRectF(
                    rect.left() + column * step,
                    rect.top() + row * step,
                    step,
                    step,
                )
            )


class ColorSwatch(QPushButton):
    """Quadrado clicável da paleta. Esquerdo define a primária, direito a secundária."""

    picked = Signal(QColor, bool)

    def __init__(self, color: QColor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"{self._color.name().upper()} — direito define a cor de fundo")

    @property
    def color(self) -> QColor:
        return QColor(self._color)

    def set_color(self, color: QColor) -> None:
        self._color = QColor(color)
        self.setToolTip(f"{self._color.name().upper()} — direito define a cor de fundo")
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self.picked.emit(self.color, True)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.picked.emit(self.color, False)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(1.5, 1.5, self.width() - 3.0, self.height() - 3.0)
        if self._color.alpha() < 255:
            _checkerboard(painter, rect)
        painter.setBrush(self._color)
        painter.setPen(QPen(QColor(PALETTE.border_strong), 1.0))
        painter.drawRoundedRect(rect, 4.0, 4.0)
        painter.end()


class ColorPairWidget(QWidget):
    """As duas cores ativas, empilhadas."""

    edit_requested = Signal(bool)

    def __init__(self, settings: ToolSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setFixedSize(78, 78)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Clique duas vezes para escolher a cor")

    def _primary_rect(self) -> QRectF:
        return QRectF(2.0, 2.0, 46.0, 46.0)

    def _secondary_rect(self) -> QRectF:
        return QRectF(30.0, 30.0, 46.0, 46.0)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        for rect, color in (
            (self._secondary_rect(), self._settings.secondary),
            (self._primary_rect(), self._settings.primary),
        ):
            if color.alpha() < 255:
                _checkerboard(painter, rect)
            painter.setBrush(color)
            painter.setPen(QPen(QColor(PALETTE.border_strong), 1.4))
            painter.drawRoundedRect(rect, 6.0, 6.0)
        painter.end()

    def mouseDoubleClickEvent(self, event) -> None:
        self.edit_requested.emit(
            self._secondary_rect().contains(event.position())
            and not self._primary_rect().contains(event.position())
        )


class ColorPanel(QWidget):
    """Painel completo de cores."""

    def __init__(self, settings: ToolSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._recent_swatches: list[ColorSwatch] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self._build_active_row())
        layout.addWidget(self._build_palette())
        layout.addWidget(self._build_recent())
        layout.addStretch(1)

        settings.colors_changed.connect(self._on_colors_changed)

    # ------------------------------------------------------------------ blocos

    def _build_active_row(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self._pair = ColorPairWidget(self._settings)
        self._pair.edit_requested.connect(self.edit_color)
        row.addWidget(self._pair)

        buttons = QVBoxLayout()
        buttons.setSpacing(6)

        swap = QPushButton("Trocar")
        swap.setProperty("variant", "ghost")
        swap.setToolTip("Trocar cor de frente e de fundo (X)")
        swap.clicked.connect(self._settings.swap_colors)
        buttons.addWidget(swap)

        edit = QPushButton("Editar cor…")
        edit.clicked.connect(lambda: self.edit_color(False))
        buttons.addWidget(edit)
        buttons.addStretch(1)

        row.addLayout(buttons)
        row.addStretch(1)
        return container

    def _build_palette(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel("Paleta")
        label.setProperty("role", "section")
        layout.addWidget(label)

        grid = QGridLayout()
        grid.setSpacing(4)
        for index, value in enumerate(STANDARD_COLORS):
            swatch = ColorSwatch(QColor(value))
            swatch.picked.connect(self._apply_color)
            grid.addWidget(swatch, index // PALETTE_COLUMNS, index % PALETTE_COLUMNS)
        layout.addLayout(grid)
        return container

    def _build_recent(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel("Usadas recentemente")
        label.setProperty("role", "section")
        layout.addWidget(label)

        self._recent_grid = QGridLayout()
        self._recent_grid.setSpacing(4)
        layout.addLayout(self._recent_grid)
        self._rebuild_recent()
        return container

    # ------------------------------------------------------------------ ações

    def _apply_color(self, color: QColor, secondary: bool) -> None:
        if secondary:
            self._settings.secondary = color
        else:
            self._settings.primary = color

    def edit_color(self, secondary: bool = False) -> None:
        """Abre o seletor completo do sistema para a cor pedida."""
        current = self._settings.secondary if secondary else self._settings.primary
        chosen = QColorDialog.getColor(
            current,
            self,
            "Cor de fundo" if secondary else "Cor de frente",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if chosen.isValid():
            self._apply_color(chosen, secondary)

    def _on_colors_changed(self) -> None:
        self._pair.update()
        self._rebuild_recent()

    def _rebuild_recent(self) -> None:
        while self._recent_grid.count():
            item = self._recent_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        for index, color in enumerate(self._settings.recent_colors):
            swatch = ColorSwatch(color)
            swatch.picked.connect(self._apply_color)
            self._recent_grid.addWidget(
                swatch, index // PALETTE_COLUMNS, index % PALETTE_COLUMNS
            )

    def sizeHint(self) -> QSize:
        return QSize(280, 320)
