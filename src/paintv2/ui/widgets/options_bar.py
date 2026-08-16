"""Barra de opções contextual da ferramenta ativa.

Todos os controles existem uma vez só e são mostrados ou escondidos conforme a
ferramenta declara em ``Tool.options``. Assim o tamanho ajustado no pincel
continua valendo na borracha e na saturação — é o mesmo controle, não uma cópia.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFontComboBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...core.brush_modes import MODES_BY_KEY
from ...core.brush_tips import MAX_SIZE, MIN_SIZE, TIPS
from ...tools.base import Tool
from ...tools.settings import (
    BRUSH_SLIDER_MAX,
    SHAPE_FILL_NONE,
    SHAPE_FILL_PRIMARY,
    SHAPE_FILL_SECONDARY,
    ToolSettings,
)
from ...tools.shapes import SHAPES

SLIDER_WIDTH = 132


class OptionsBar(QWidget):
    """Faixa horizontal com os parâmetros da ferramenta ativa."""

    def __init__(self, settings: ToolSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._blocks: dict[str, QWidget] = {}
        self._active_mode = "paint"

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(14, 8, 14, 8)
        self._layout.setSpacing(16)

        self._build_blocks()
        self._layout.addStretch(1)

        settings.changed.connect(self._sync_from_settings)
        self.show_for(None)

    # ----------------------------------------------------------------- blocos

    def _build_blocks(self) -> None:
        self._add_block("tip", "Ponta", self._build_tip())
        self._add_block("size", "Tamanho", self._build_size())
        self._add_block("amount", "Intensidade", self._build_amount())
        self._add_block("opacity", "Opacidade", self._build_opacity())
        self._add_block("tolerance", "Tolerância", self._build_tolerance())
        self._add_block("fill_contiguous", "", self._build_fill_contiguous())
        self._add_block("erase_transparent", "", self._build_erase_transparent())
        self._add_block("shape_kind", "Forma", self._build_shape_kind())
        self._add_block("shape_fill", "Preenchimento", self._build_shape_fill())
        self._add_block("line_width", "Espessura", self._build_line_width())
        self._add_block("font_family", "Fonte", self._build_font_family())
        self._add_block("font_size", "Corpo", self._build_font_size())
        self._add_block("font_style", "Estilo", self._build_font_style())
        self._add_block("antialias", "", self._build_antialias())

    def _add_block(self, key: str, title: str, control: QWidget) -> None:
        block = QWidget()
        layout = QVBoxLayout(block)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        if title:
            label = QLabel(title)
            label.setProperty("role", "section")
            layout.addWidget(label)
            self._blocks[f"{key}__label"] = label
        layout.addWidget(control)

        self._layout.addWidget(block)
        self._blocks[key] = block

    # ---------------------------------------------------------------- controles

    def _build_tip(self) -> QWidget:
        self._tip_combo = QComboBox()
        self._tip_combo.setMinimumWidth(160)
        for tip in TIPS:
            self._tip_combo.addItem(tip.label, tip.key)
            self._tip_combo.setItemData(
                self._tip_combo.count() - 1, tip.description, Qt.ItemDataRole.ToolTipRole
            )
        self._tip_combo.currentIndexChanged.connect(
            lambda: setattr(self._settings, "tip_key", self._tip_combo.currentData())
        )
        return self._tip_combo

    def _build_size(self) -> QWidget:
        # A rampa vai até 1000 para continuar utilizável no arraste; o campo
        # aceita o pincel inteiro, para quem precisa cobrir uma foto 4K de uma vez.
        self._size_slider, self._size_spin, widget = _slider_with_spin(
            int(MIN_SIZE), BRUSH_SLIDER_MAX, spin_maximum=int(MAX_SIZE)
        )
        self._size_spin.setToolTip(
            f"Até {int(MAX_SIZE)} px — digite valores acima de {BRUSH_SLIDER_MAX}"
        )
        self._size_slider.valueChanged.connect(
            lambda value: setattr(self._settings, "brush_size", value)
        )
        self._size_spin.valueChanged.connect(
            lambda value: setattr(self._settings, "brush_size", value)
        )
        return widget

    def _build_amount(self) -> QWidget:
        self._amount_slider, self._amount_spin, widget = _slider_with_spin(-100, 100)
        self._amount_slider.valueChanged.connect(self._on_amount_changed)
        self._amount_spin.valueChanged.connect(self._on_amount_changed)
        return widget

    def _build_opacity(self) -> QWidget:
        self._opacity_slider, self._opacity_spin, widget = _slider_with_spin(1, 100)
        self._opacity_slider.valueChanged.connect(
            lambda value: setattr(self._settings, "opacity", value)
        )
        self._opacity_spin.valueChanged.connect(
            lambda value: setattr(self._settings, "opacity", value)
        )
        return widget

    def _build_tolerance(self) -> QWidget:
        self._tolerance_slider, self._tolerance_spin, widget = _slider_with_spin(0, 100)
        self._tolerance_slider.valueChanged.connect(
            lambda value: setattr(self._settings, "tolerance", value)
        )
        self._tolerance_spin.valueChanged.connect(
            lambda value: setattr(self._settings, "tolerance", value)
        )
        return widget

    def _build_fill_contiguous(self) -> QWidget:
        self._contiguous_check = QCheckBox("Somente a área conectada")
        self._contiguous_check.setToolTip(
            "Desmarcado, preenche todos os pixels parecidos da imagem inteira."
        )
        self._contiguous_check.toggled.connect(
            lambda value: setattr(self._settings, "fill_contiguous", value)
        )
        return self._contiguous_check

    def _build_erase_transparent(self) -> QWidget:
        self._transparent_check = QCheckBox("Apagar para transparente")
        self._transparent_check.setToolTip(
            "Desmarcado, a borracha pinta com a cor de fundo, como no Paint."
        )
        self._transparent_check.toggled.connect(
            lambda value: setattr(self._settings, "erase_to_transparent", value)
        )
        return self._transparent_check

    def _build_shape_kind(self) -> QWidget:
        self._shape_combo = QComboBox()
        self._shape_combo.setMinimumWidth(180)
        for shape in SHAPES:
            self._shape_combo.addItem(shape.label, shape.key)
        self._shape_combo.currentIndexChanged.connect(
            lambda: setattr(self._settings, "shape_kind", self._shape_combo.currentData())
        )
        return self._shape_combo

    def _build_shape_fill(self) -> QWidget:
        self._fill_combo = QComboBox()
        self._fill_combo.addItem("Sem preenchimento", SHAPE_FILL_NONE)
        self._fill_combo.addItem("Cor de fundo", SHAPE_FILL_SECONDARY)
        self._fill_combo.addItem("Cor de frente", SHAPE_FILL_PRIMARY)
        self._fill_combo.currentIndexChanged.connect(
            lambda: setattr(self._settings, "shape_fill", self._fill_combo.currentData())
        )
        return self._fill_combo

    def _build_line_width(self) -> QWidget:
        self._line_spin = QSpinBox()
        self._line_spin.setRange(1, 100)
        self._line_spin.setSuffix(" px")
        self._line_spin.valueChanged.connect(
            lambda value: setattr(self._settings, "line_width", value)
        )
        return self._line_spin

    def _build_font_family(self) -> QWidget:
        self._font_combo = QFontComboBox()
        self._font_combo.setMinimumWidth(180)
        self._font_combo.currentFontChanged.connect(
            lambda font: setattr(self._settings, "font_family", font.family())
        )
        return self._font_combo

    def _build_font_size(self) -> QWidget:
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(4, 400)
        self._font_size_spin.setSuffix(" px")
        self._font_size_spin.valueChanged.connect(
            lambda value: setattr(self._settings, "font_size", value)
        )
        return self._font_size_spin

    def _build_font_style(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._bold_button = QToolButton()
        self._bold_button.setText("N")
        self._bold_button.setCheckable(True)
        self._bold_button.setToolTip("Negrito")
        self._bold_button.toggled.connect(
            lambda value: setattr(self._settings, "font_bold", value)
        )

        self._italic_button = QToolButton()
        self._italic_button.setText("I")
        self._italic_button.setCheckable(True)
        self._italic_button.setToolTip("Itálico")
        self._italic_button.toggled.connect(
            lambda value: setattr(self._settings, "font_italic", value)
        )

        layout.addWidget(self._bold_button)
        layout.addWidget(self._italic_button)
        return container

    def _build_antialias(self) -> QWidget:
        self._antialias_check = QCheckBox("Suavizar bordas")
        self._antialias_check.toggled.connect(
            lambda value: setattr(self._settings, "antialias", value)
        )
        return self._antialias_check

    # ------------------------------------------------------------------ estado

    def show_for(self, tool: Tool | None) -> None:
        """Mostra apenas os controles declarados pela ferramenta."""
        visible = set(tool.options) if tool is not None else set()
        self._active_mode = getattr(tool, "mode_key", "paint") if tool else "paint"

        for key, widget in self._blocks.items():
            if key.endswith("__label"):
                continue
            widget.setVisible(key in visible)

        if "amount" in visible:
            self._configure_amount()
        self._sync_from_settings()

    def _configure_amount(self) -> None:
        definition = MODES_BY_KEY.get(self._active_mode)
        if definition is None:
            return
        label = self._blocks.get("amount__label")
        if isinstance(label, QLabel):
            label.setText(definition.amount_label)
        for control in (self._amount_slider, self._amount_spin):
            control.blockSignals(True)
            control.setRange(definition.amount_min, definition.amount_max)
            control.blockSignals(False)
        self._amount_spin.setSuffix(definition.amount_suffix)

        # Numa faixa que passa pelo zero, preencher o trilho desde a esquerda
        # daria a impressão de valor alto no neutro. Mudar a propriedade exige
        # repolir o widget para o Qt reavaliar a folha de estilo.
        self._amount_slider.setProperty("bipolar", definition.amount_min < 0)
        self._amount_slider.style().unpolish(self._amount_slider)
        self._amount_slider.style().polish(self._amount_slider)

    def _on_amount_changed(self, value: int) -> None:
        self._settings.set_amount(self._active_mode, int(value))

    def _sync_from_settings(self) -> None:
        """Reflete o estado atual sem disparar de volta os sinais dos controles."""
        pairs = (
            (self._size_slider, self._settings.brush_size),
            (self._size_spin, self._settings.brush_size),
            (self._opacity_slider, self._settings.opacity),
            (self._opacity_spin, self._settings.opacity),
            (self._tolerance_slider, self._settings.tolerance),
            (self._tolerance_spin, self._settings.tolerance),
            (self._amount_slider, self._settings.amount(self._active_mode)),
            (self._amount_spin, self._settings.amount(self._active_mode)),
            (self._line_spin, self._settings.line_width),
            (self._font_size_spin, self._settings.font_size),
        )
        for control, value in pairs:
            _set_silently(control, value)

        _set_silently(self._contiguous_check, self._settings.fill_contiguous)
        _set_silently(self._transparent_check, self._settings.erase_to_transparent)
        _set_silently(self._antialias_check, self._settings.antialias)
        _set_silently(self._bold_button, self._settings.font_bold)
        _set_silently(self._italic_button, self._settings.font_italic)
        _select_data(self._tip_combo, self._settings.tip_key)
        _select_data(self._shape_combo, self._settings.shape_kind)
        _select_data(self._fill_combo, self._settings.shape_fill)


def _slider_with_spin(
    minimum: int, maximum: int, spin_maximum: int | None = None
) -> tuple[QSlider, QSpinBox, QWidget]:
    """Rampa e campo numérico sincronizados.

    O campo pode aceitar mais que a rampa: nesse caso a rampa fica no fim e o
    valor real continua sendo o do campo — é o que permite um pincel de 3000 px
    sem transformar cada pixel da rampa num salto grosseiro.
    """
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(minimum, maximum)
    slider.setFixedWidth(SLIDER_WIDTH)

    spin = QSpinBox()
    spin.setRange(minimum, spin_maximum or maximum)
    spin.setFixedWidth(74)

    slider.valueChanged.connect(lambda value: _set_silently(spin, value))
    spin.valueChanged.connect(lambda value: _set_silently(slider, value))

    layout.addWidget(slider)
    layout.addWidget(spin)
    return slider, spin, container


def _set_silently(control, value) -> None:
    control.blockSignals(True)
    if isinstance(control, (QSlider, QSpinBox)):
        control.setValue(int(value))
    else:
        control.setChecked(bool(value))
    control.blockSignals(False)


def _select_data(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    if index >= 0 and index != combo.currentIndex():
        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)
