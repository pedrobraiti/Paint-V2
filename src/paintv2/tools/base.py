"""Contrato das ferramentas e utilidades comuns a todas elas.

Uma ferramenta traduz eventos de mouse em chamadas do núcleo. Ela nunca desenha
pixels por conta própria: pede ao motor de traço, ao balde ou ao ``QPainter``, e
sempre registra no histórico o que alterou.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QCursor, QPainter

from ..core.brush_tips import get_tip
from ..core.document import Document
from ..core.pixels import Rect
from ..core.selection import Selection
from ..core.stroke import StrokeEngine
from .settings import ToolSettings

if TYPE_CHECKING:  # pragma: no cover - apenas para tipagem
    from ..ui.canvas_view import CanvasView


@dataclass(frozen=True)
class CanvasEvent:
    """Evento de ponteiro já convertido para coordenadas do documento."""

    position: QPointF
    button: Qt.MouseButton = Qt.MouseButton.NoButton
    buttons: Qt.MouseButton = Qt.MouseButton.NoButton
    modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
    pressure: float = 1.0

    @property
    def x(self) -> float:
        return self.position.x()

    @property
    def y(self) -> float:
        return self.position.y()

    @property
    def pixel(self) -> tuple[int, int]:
        return int(np.floor(self.position.x())), int(np.floor(self.position.y()))

    @property
    def is_secondary(self) -> bool:
        """Botão direito: no Paint, desenha com a cor secundária."""
        return bool(self.button & Qt.MouseButton.RightButton) or bool(
            self.buttons & Qt.MouseButton.RightButton
        )

    @property
    def constrained(self) -> bool:
        """Shift: restringe a proporção, o ângulo ou o eixo."""
        return bool(self.modifiers & Qt.KeyboardModifier.ShiftModifier)

    @property
    def from_center(self) -> bool:
        """Ctrl: desenha a forma a partir do centro."""
        return bool(self.modifiers & Qt.KeyboardModifier.ControlModifier)


class ToolContext(Protocol):
    """O que a ferramenta enxerga do editor."""

    @property
    def document(self) -> Document: ...

    @property
    def selection(self) -> Selection: ...

    @property
    def settings(self) -> ToolSettings: ...

    def refresh(self, rect: Rect | None = None) -> None: ...

    def refresh_overlay(self) -> None: ...

    def notify_document_changed(self) -> None: ...

    def show_hint(self, message: str) -> None: ...

    def zoom_at(self, document_point: QPointF, factor: float) -> None: ...

    def pan_by(self, document_delta: QPointF) -> None: ...

    def activate_previous_tool(self) -> None: ...

    def set_selection_outline(self, outline) -> None: ...

    def document_transform(self): ...

    def canvas_widget(self) -> "CanvasView": ...


class Tool:
    """Base de todas as ferramentas."""

    key: str = ""
    label: str = ""
    icon: str = "brush"
    shortcut: str = ""
    hint: str = ""
    group: str = "desenho"
    options: tuple[str, ...] = ()
    cursor_shape: Qt.CursorShape = Qt.CursorShape.CrossCursor
    shows_brush_outline: bool = False

    def __init__(self, context: ToolContext) -> None:
        self.context = context

    # ------------------------------------------------------------------ ciclo

    def activate(self) -> None:
        """Chamado quando a ferramenta é selecionada."""

    def deactivate(self) -> None:
        """Chamado antes de trocar de ferramenta; deve confirmar pendências."""
        self.commit_pending()

    def commit_pending(self) -> None:
        """Fecha operações em andamento (texto digitado, curva não terminada)."""

    # ---------------------------------------------------------------- eventos

    def press(self, event: CanvasEvent) -> None: ...

    def move(self, event: CanvasEvent) -> None: ...

    def release(self, event: CanvasEvent) -> None: ...

    def double_click(self, event: CanvasEvent) -> None: ...

    def key_press(self, key: int, modifiers: Qt.KeyboardModifier) -> bool:
        """Devolve ``True`` se consumiu a tecla."""
        return False

    def paint_overlay(self, painter: QPainter, view: "CanvasView") -> None:
        """Desenha guias temporárias por cima da tela (não altera pixels)."""

    def on_view_changed(self) -> None:
        """Chamado quando zoom ou deslocamento mudam; reposiciona editores inline."""

    def cursor(self) -> QCursor:
        return QCursor(self.cursor_shape)

    # --------------------------------------------------------------- ajudantes

    @property
    def document(self) -> Document:
        return self.context.document

    @property
    def settings(self) -> ToolSettings:
        return self.context.settings

    def active_color(self, event: CanvasEvent) -> QColor:
        """Cor primária, ou a secundária quando o traço vem do botão direito."""
        return self.settings.secondary if event.is_secondary else self.settings.primary

    def other_color(self, event: CanvasEvent) -> QColor:
        return self.settings.primary if event.is_secondary else self.settings.secondary


def color_to_array(color: QColor) -> np.ndarray:
    """``QColor`` para RGBA ``float32`` em ``[0, 1]``."""
    return np.array(
        [color.redF(), color.greenF(), color.blueF(), color.alphaF()], dtype=np.float32
    )


def color_to_uint8(color: QColor) -> np.ndarray:
    return np.array([color.red(), color.green(), color.blue(), color.alpha()], np.uint8)


def make_stroke_engine(
    document: Document,
    selection: Selection,
    tip_key: str,
    mode,
    size: float,
) -> StrokeEngine:
    """Monta o motor de traço já preso à seleção ativa, se houver."""
    return StrokeEngine(
        pixels=document.pixels,
        tip=get_tip(tip_key),
        mode=mode,
        size=size,
        buffers=document.stroke_buffers,
        clip_mask=selection.clip_weights(),
    )
