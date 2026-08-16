"""Ferramentas de traço livre.

Todas compartilham o mesmo caminho — pressionar, arrastar, soltar, registrar no
histórico — e diferem apenas no modo que entregam ao motor. É por isso que
saturação, blend, desfoque e companhia funcionam com qualquer ponta, Spray
inclusive.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer

from ..core import brush_modes
from ..core.brush_modes import BrushMode
from ..core.brush_tips import get_tip
from .base import CanvasEvent, Tool, ToolContext, color_to_array, make_stroke_engine
from .settings import DEFAULT_SPRAY_RATE_MS

BRUSH_OPTIONS = ("tip", "size", "amount", "opacity")


class StrokeTool(Tool):
    """Base das ferramentas que aplicam um modo ao longo de um caminho."""

    mode_key = "paint"
    forced_tip: str | None = None
    shows_brush_outline = True
    group = "desenho"
    options = BRUSH_OPTIONS

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self._engine = None
        self._dwell_timer = QTimer()
        self._dwell_timer.setInterval(DEFAULT_SPRAY_RATE_MS)
        self._dwell_timer.timeout.connect(self._on_dwell)

    # ------------------------------------------------------------------ modo

    @property
    def tip_key(self) -> str:
        return self.forced_tip or self.settings.tip_key

    @property
    def amount(self) -> float:
        """Intensidade do efeito, normalizada conforme a faixa do modo."""
        definition = brush_modes.MODES_BY_KEY[self.mode_key]
        raw = self.settings.amount(self.mode_key)
        scale = max(abs(definition.amount_min), abs(definition.amount_max)) or 1
        return raw / scale

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        raise NotImplementedError

    # --------------------------------------------------------------- eventos

    def press(self, event: CanvasEvent) -> None:
        if event.button not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        self._engine = make_stroke_engine(
            self.document,
            self.context.selection,
            self.tip_key,
            self.create_mode(event),
            float(self.settings.brush_size),
        )
        self.context.refresh(self._engine.begin(event.x, event.y, event.pressure))
        if self._engine.builds_up:
            self._dwell_timer.start()

    def move(self, event: CanvasEvent) -> None:
        if self._engine is None:
            return
        self.context.refresh(self._engine.move(event.x, event.y, event.pressure))

    def release(self, event: CanvasEvent) -> None:
        self._finish()

    def deactivate(self) -> None:
        self._finish()

    def _on_dwell(self) -> None:
        if self._engine is None:
            return
        self.context.refresh(self._engine.dwell())

    def _finish(self) -> None:
        self._dwell_timer.stop()
        if self._engine is None:
            return
        engine, self._engine = self._engine, None
        rect = engine.end()
        if rect is not None:
            self.document.commit_patch(self.label, rect, engine.original_region(rect))
            self.context.notify_document_changed()
        self.context.refresh(rect)


class PencilTool(StrokeTool):
    key = "pencil"
    label = "Lápis"
    icon = "pencil"
    shortcut = "P"
    hint = "Traço duro sem suavização. Botão direito usa a cor secundária."
    forced_tip = "pencil"
    options = ("size",)

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        return brush_modes.PaintMode(color_to_array(self.active_color(event)), 1.0)


class BrushTool(StrokeTool):
    key = "brush"
    label = "Pincel"
    icon = "brush"
    shortcut = "B"
    hint = "Pinta com a ponta escolhida. Botão direito usa a cor secundária."
    options = ("tip", "size", "opacity")

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        return brush_modes.PaintMode(
            color_to_array(self.active_color(event)), self.settings.opacity / 100.0
        )


class SprayTool(BrushTool):
    key = "spray"
    label = "Spray"
    icon = "spray"
    shortcut = "A"
    hint = "Aerógrafo: segure parado para depositar mais tinta."
    forced_tip = "airbrush"
    options = ("size", "opacity")


class EraserTool(StrokeTool):
    key = "eraser"
    label = "Borracha"
    icon = "eraser"
    shortcut = "E"
    hint = "Apaga para a cor de fundo, ou para transparente se a opção estiver marcada."
    mode_key = "erase"
    options = ("tip", "size", "amount", "erase_transparent")

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        background = (
            None
            if self.settings.erase_to_transparent
            else color_to_array(self.other_color(event))
        )
        return brush_modes.EraseMode(self.amount, background)


class SaturationBrushTool(StrokeTool):
    key = "saturation"
    label = "Saturação"
    icon = "saturation"
    shortcut = "S"
    hint = "Satura (ou dessatura, com valor negativo) só onde o pincel passa."
    mode_key = "saturation"
    group = "efeitos"

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        amount = -self.amount if event.is_secondary else self.amount
        return brush_modes.SaturationMode(amount, self.settings.opacity / 100.0)


class BlendBrushTool(StrokeTool):
    key = "blend"
    label = "Blend"
    icon = "blend"
    shortcut = "G"
    hint = "Arrasta e funde as cores vizinhas — dissolve vincos e emendas."
    mode_key = "blend"
    group = "efeitos"

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        return brush_modes.BlendSmudgeMode(self.amount)


class BlurBrushTool(StrokeTool):
    key = "blur"
    label = "Desfoque"
    icon = "blur"
    shortcut = "U"
    hint = "Suaviza detalhes na área pincelada."
    mode_key = "blur"
    group = "efeitos"

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        return brush_modes.BlurMode(
            self.amount, float(self.settings.brush_size), self.settings.opacity / 100.0
        )


class SharpenBrushTool(StrokeTool):
    key = "sharpen"
    label = "Nitidez"
    icon = "sharpen"
    shortcut = "H"
    hint = "Realça bordas e microcontraste na área pincelada."
    mode_key = "sharpen"
    group = "efeitos"

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        return brush_modes.SharpenMode(self.amount, self.settings.opacity / 100.0)


class DodgeBrushTool(StrokeTool):
    key = "dodge"
    label = "Clarear"
    icon = "dodge"
    shortcut = "O"
    hint = "Clareia progressivamente. Botão direito escurece."
    mode_key = "dodge"
    group = "efeitos"

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        if event.is_secondary:
            return brush_modes.BurnMode(self.amount, self.settings.opacity / 100.0)
        return brush_modes.DodgeMode(self.amount, self.settings.opacity / 100.0)


class BurnBrushTool(StrokeTool):
    key = "burn"
    label = "Escurecer"
    icon = "burn"
    shortcut = "I"
    hint = "Escurece progressivamente. Botão direito clareia."
    mode_key = "burn"
    group = "efeitos"

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        if event.is_secondary:
            return brush_modes.DodgeMode(self.amount, self.settings.opacity / 100.0)
        return brush_modes.BurnMode(self.amount, self.settings.opacity / 100.0)


class HueBrushTool(StrokeTool):
    key = "hue"
    label = "Matiz"
    icon = "hue"
    shortcut = "J"
    hint = "Gira a cor da área pincelada sem mexer no brilho."
    mode_key = "hue"
    group = "efeitos"

    def create_mode(self, event: CanvasEvent) -> BrushMode:
        degrees = self.settings.amount("hue")
        if event.is_secondary:
            degrees = -degrees
        return brush_modes.HueMode(degrees, self.settings.opacity / 100.0)


STROKE_TOOLS: tuple[type[StrokeTool], ...] = (
    PencilTool,
    BrushTool,
    SprayTool,
    EraserTool,
    SaturationBrushTool,
    BlendBrushTool,
    BlurBrushTool,
    SharpenBrushTool,
    DodgeBrushTool,
    BurnBrushTool,
    HueBrushTool,
)


def tip_of(tool: StrokeTool) -> str:
    """Rótulo da ponta em uso, para a barra de status."""
    return get_tip(tool.tip_key).label
