"""Ajustes globais de imagem, com pré-visualização ao vivo.

A prévia é escrita direto no buffer do documento — é o único jeito de o usuário
ver o efeito no tamanho real, com zoom e tudo. Os pixels originais ficam guardados
e voltam ao lugar se o diálogo for cancelado; só ao confirmar a alteração entra no
histórico.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.adjustments import AdjustmentSettings, apply_adjustments
from ...core.document import Document
from ...core.pixels import view

PREVIEW_DELAY_MS = 90

SLIDERS: tuple[tuple[str, str, int, int], ...] = (
    ("exposure", "Exposição", -100, 100),
    ("brightness", "Brilho", -100, 100),
    ("contrast", "Contraste", -100, 100),
    ("saturation", "Saturação", -100, 200),
    ("vibrance", "Vibração", -100, 100),
    ("hue", "Matiz", -180, 180),
    ("temperature", "Temperatura", -100, 100),
    ("tint", "Tonalidade", -100, 100),
)

TOGGLES: tuple[tuple[str, str], ...] = (
    ("grayscale", "Preto e branco"),
    ("sepia", "Sépia"),
    ("invert", "Inverter cores"),
)


class AdjustmentsDialog(QDialog):
    """Painel de ajustes com prévia aplicada ao documento."""

    def __init__(
        self,
        document: Document,
        canvas,
        restrict_to_selection: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Ajustes de imagem")
        self.setModal(True)

        self._document = document
        self._canvas = canvas
        self._settings = AdjustmentSettings()
        self._sliders: dict[str, QSlider] = {}
        self._spins: dict[str, QSpinBox] = {}
        self._toggles: dict[str, QCheckBox] = {}

        selection = canvas.selection
        self._rect = (
            selection.bounds
            if restrict_to_selection and selection.bounds is not None
            else document.bounds
        )
        self._mask = selection.mask if restrict_to_selection else None
        self._original = view(document.pixels, self._rect).copy()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(PREVIEW_DELAY_MS)
        self._timer.timeout.connect(self._render_preview)

        self._build_ui(restrict_to_selection)

    # --------------------------------------------------------------- interface

    def _build_ui(self, restricted: bool) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(14)

        if restricted:
            note = QLabel("Aplicando somente dentro da seleção.")
            note.setProperty("role", "muted")
            layout.addWidget(note)

        tone = QGroupBox("Tom e cor")
        grid = QGridLayout(tone)
        grid.setSpacing(8)
        for row, (key, label, minimum, maximum) in enumerate(SLIDERS):
            grid.addWidget(QLabel(label), row, 0)
            slider, spin = self._build_slider(key, minimum, maximum)
            grid.addWidget(slider, row, 1)
            grid.addWidget(spin, row, 2)
        layout.addWidget(tone)

        effects = QGroupBox("Efeitos")
        effects_layout = QHBoxLayout(effects)
        effects_layout.setSpacing(16)
        for key, label in TOGGLES:
            check = QCheckBox(label)
            check.toggled.connect(lambda value, name=key: self._on_toggle(name, value))
            self._toggles[key] = check
            effects_layout.addWidget(check)
        effects_layout.addStretch(1)

        effects_layout.addWidget(QLabel("Posterizar"))
        self._posterize = QSpinBox()
        self._posterize.setRange(0, 32)
        self._posterize.setSpecialValueText("desligado")
        self._posterize.valueChanged.connect(self._on_posterize)
        effects_layout.addWidget(self._posterize)
        layout.addWidget(effects)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        reset = QPushButton("Redefinir")
        reset.setProperty("variant", "ghost")
        reset.clicked.connect(self._reset)
        buttons.addButton(reset, QDialogButtonBox.ButtonRole.ResetRole)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Aplicar")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setProperty("variant", "primary")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_slider(self, key: str, minimum: int, maximum: int):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setMinimumWidth(240)

        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setFixedWidth(78)

        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        slider.valueChanged.connect(lambda value, name=key: self._on_slider(name, value))

        self._sliders[key] = slider
        self._spins[key] = spin
        return slider, spin

    # ------------------------------------------------------------------ prévia

    def _on_slider(self, key: str, value: int) -> None:
        setattr(self._settings, key, float(value))
        self._timer.start()

    def _on_toggle(self, key: str, value: bool) -> None:
        setattr(self._settings, key, bool(value))
        self._timer.start()

    def _on_posterize(self, value: int) -> None:
        self._settings.posterize = int(value)
        self._timer.start()

    def _reset(self) -> None:
        self._settings.reset()
        for slider in self._sliders.values():
            slider.setValue(0)
        for check in self._toggles.values():
            check.setChecked(False)
        self._posterize.setValue(0)
        self._restore()

    def _render_preview(self) -> None:
        adjusted = apply_adjustments(self._original, self._settings)
        if self._mask is not None:
            adjusted = np.where(
                view(self._mask, self._rect)[..., None], adjusted, self._original
            )
        view(self._document.pixels, self._rect)[:] = adjusted
        self._canvas.refresh(self._rect)

    def _restore(self) -> None:
        view(self._document.pixels, self._rect)[:] = self._original
        self._canvas.refresh(self._rect)

    # ---------------------------------------------------------------- conclusão

    def accept(self) -> None:
        self._timer.stop()
        self._render_preview()
        if not self._settings.is_identity:
            self._document.commit_patch(
                "Ajustes de imagem", self._rect, self._original
            )
            self._canvas.notify_document_changed()
        super().accept()

    def reject(self) -> None:
        self._timer.stop()
        self._restore()
        super().reject()
