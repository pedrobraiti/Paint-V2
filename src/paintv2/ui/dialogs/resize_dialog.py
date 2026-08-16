"""Diálogo de redimensionamento de imagem e de tela."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.document import MAX_DIMENSION


@dataclass(frozen=True)
class ResizeChoice:
    width: int
    height: int
    smooth: bool


class ResizeDialog(QDialog):
    """Novo tamanho em pixels ou em porcentagem, com proporção travável."""

    def __init__(
        self,
        width: int,
        height: int,
        canvas_only: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._original = (width, height)
        self._canvas_only = canvas_only
        self._updating = False

        self.setWindowTitle("Tamanho da tela" if canvas_only else "Redimensionar imagem")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)

        description = QLabel(
            "A tela cresce ou encolhe sem esticar o conteúdo."
            if canvas_only
            else f"Tamanho atual: {width} × {height} px"
        )
        description.setProperty("role", "muted")
        layout.addWidget(description)

        self._by_pixels = QRadioButton("Em pixels")
        self._by_percent = QRadioButton("Em porcentagem")
        self._by_pixels.setChecked(True)
        self._by_pixels.toggled.connect(self._on_unit_changed)
        layout.addWidget(self._by_pixels)
        layout.addWidget(self._by_percent)

        form = QFormLayout()
        form.setSpacing(10)

        self._width = QSpinBox()
        self._width.setRange(1, MAX_DIMENSION)
        self._width.setSuffix(" px")
        self._width.setValue(width)
        self._width.valueChanged.connect(lambda value: self._sync_from(True, value))

        self._height = QSpinBox()
        self._height.setRange(1, MAX_DIMENSION)
        self._height.setSuffix(" px")
        self._height.setValue(height)
        self._height.valueChanged.connect(lambda value: self._sync_from(False, value))

        self._percent = QDoubleSpinBox()
        self._percent.setRange(1.0, 1000.0)
        self._percent.setSuffix(" %")
        self._percent.setValue(100.0)
        self._percent.setVisible(False)
        self._percent.valueChanged.connect(self._apply_percent)

        form.addRow("Largura", self._width)
        form.addRow("Altura", self._height)
        self._percent_row = QLabel("Escala")
        form.addRow(self._percent_row, self._percent)
        self._percent_row.setVisible(False)
        layout.addLayout(form)

        self._keep_ratio = QCheckBox("Manter proporção")
        self._keep_ratio.setChecked(True)
        layout.addWidget(self._keep_ratio)

        self._smooth = QCheckBox("Interpolação suave (melhor para fotos)")
        self._smooth.setChecked(True)
        self._smooth.setVisible(not canvas_only)
        layout.addWidget(self._smooth)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aplicar")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("variant", "primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ lógica

    def _on_unit_changed(self) -> None:
        by_pixels = self._by_pixels.isChecked()
        self._width.setVisible(by_pixels)
        self._height.setVisible(by_pixels)
        self._percent.setVisible(not by_pixels)
        self._percent_row.setVisible(not by_pixels)

    def _sync_from(self, from_width: bool, value: int) -> None:
        if self._updating or not self._keep_ratio.isChecked():
            return
        original_width, original_height = self._original
        self._updating = True
        if from_width:
            self._height.setValue(max(1, round(value * original_height / original_width)))
        else:
            self._width.setValue(max(1, round(value * original_width / original_height)))
        self._updating = False

    def _apply_percent(self, percent: float) -> None:
        original_width, original_height = self._original
        self._updating = True
        self._width.setValue(max(1, round(original_width * percent / 100.0)))
        self._height.setValue(max(1, round(original_height * percent / 100.0)))
        self._updating = False

    def choice(self) -> ResizeChoice:
        return ResizeChoice(
            width=self._width.value(),
            height=self._height.value(),
            smooth=self._smooth.isChecked() and not self._canvas_only,
        )
