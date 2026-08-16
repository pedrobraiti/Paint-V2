"""Diálogo de nova tela em branco."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.document import MAX_DIMENSION

PRESETS: tuple[tuple[str, int, int], ...] = (
    ("Personalizado", 0, 0),
    ("Full HD — 1920 × 1080", 1920, 1080),
    ("HD — 1280 × 720", 1280, 720),
    ("4K UHD — 3840 × 2160", 3840, 2160),
    ("Quadrado — 1080 × 1080", 1080, 1080),
    ("Story — 1080 × 1920", 1080, 1920),
    ("A4 a 300 dpi — 2480 × 3508", 2480, 3508),
    ("Papel de parede — 2560 × 1440", 2560, 1440),
    ("Ícone — 512 × 512", 512, 512),
)

BACKGROUND_WHITE = "white"
BACKGROUND_TRANSPARENT = "transparent"
BACKGROUND_CUSTOM = "custom"


@dataclass(frozen=True)
class NewImageChoice:
    """Resultado do diálogo."""

    width: int
    height: int
    color: tuple[int, int, int, int]


class NewImageDialog(QDialog):
    """Escolha de dimensões e fundo para uma tela nova."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nova imagem")
        self.setModal(True)
        self._custom_color = QColor(255, 255, 255, 255)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(16)

        form = QFormLayout()
        form.setSpacing(10)

        self._preset = QComboBox()
        for label, width, height in PRESETS:
            self._preset.addItem(label, (width, height))
        self._preset.currentIndexChanged.connect(self._apply_preset)
        form.addRow("Predefinição", self._preset)

        self._width = _dimension_spin(1920)
        self._height = _dimension_spin(1080)
        self._width.valueChanged.connect(self._mark_custom)
        self._height.valueChanged.connect(self._mark_custom)
        form.addRow("Largura", self._width)
        form.addRow("Altura", self._height)

        self._background = QComboBox()
        self._background.addItem("Branco", BACKGROUND_WHITE)
        self._background.addItem("Transparente", BACKGROUND_TRANSPARENT)
        self._background.addItem("Cor personalizada…", BACKGROUND_CUSTOM)
        self._background.currentIndexChanged.connect(self._on_background_changed)
        form.addRow("Fundo", self._background)

        layout.addLayout(form)

        self._summary = QLabel()
        self._summary.setProperty("role", "muted")
        layout.addWidget(self._summary)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Criar")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("variant", "primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._preset.setCurrentIndex(1)
        self._update_summary()

    # ------------------------------------------------------------------ ações

    def _apply_preset(self, index: int) -> None:
        width, height = self._preset.itemData(index)
        if not width or not height:
            return
        for control, value in ((self._width, width), (self._height, height)):
            control.blockSignals(True)
            control.setValue(value)
            control.blockSignals(False)
        self._update_summary()

    def _mark_custom(self) -> None:
        if self._preset.currentIndex() != 0:
            self._preset.blockSignals(True)
            self._preset.setCurrentIndex(0)
            self._preset.blockSignals(False)
        self._update_summary()

    def _on_background_changed(self) -> None:
        if self._background.currentData() != BACKGROUND_CUSTOM:
            return
        chosen = QColorDialog.getColor(
            self._custom_color,
            self,
            "Cor de fundo",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if chosen.isValid():
            self._custom_color = chosen
        else:
            self._background.setCurrentIndex(0)

    def _update_summary(self) -> None:
        megapixels = self._width.value() * self._height.value() / 1_000_000
        self._summary.setText(f"{megapixels:.1f} megapixels")

    # ---------------------------------------------------------------- resultado

    def choice(self) -> NewImageChoice:
        kind = self._background.currentData()
        if kind == BACKGROUND_TRANSPARENT:
            color = (0, 0, 0, 0)
        elif kind == BACKGROUND_CUSTOM:
            color = (
                self._custom_color.red(),
                self._custom_color.green(),
                self._custom_color.blue(),
                self._custom_color.alpha(),
            )
        else:
            color = (255, 255, 255, 255)
        return NewImageChoice(self._width.value(), self._height.value(), color)


def _dimension_spin(default: int) -> QSpinBox:
    spin = QSpinBox()
    spin.setRange(1, MAX_DIMENSION)
    spin.setSuffix(" px")
    spin.setValue(default)
    spin.setAlignment(Qt.AlignmentFlag.AlignRight)
    return spin
