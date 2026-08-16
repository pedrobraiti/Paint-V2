"""Balde de tinta, conta-gotas, lupa e mão."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QCursor

from ..core.fill import compute_fill_region
from .base import CanvasEvent, Tool, color_to_uint8

ZOOM_STEP = 1.6


class FillTool(Tool):
    key = "fill"
    label = "Balde de tinta"
    icon = "fill"
    shortcut = "F"
    hint = "Clique para preencher. A tolerância decide o quanto de variação entra junto."
    group = "desenho"
    options = ("tolerance", "fill_contiguous")

    def press(self, event: CanvasEvent) -> None:
        if event.button not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        origin_x, origin_y = event.pixel
        selection = self.context.selection
        found = compute_fill_region(
            self.document.pixels,
            origin_x,
            origin_y,
            tolerance=float(self.settings.tolerance),
            contiguous=self.settings.fill_contiguous,
            clip=selection.mask,
        )
        if found is None:
            return

        region, rect = found
        before = self.document.snapshot_region(rect)
        if before is None:
            return
        self.document.pixels[region] = color_to_uint8(self.active_color(event))
        self.document.commit_patch(self.label, rect, before)
        self.context.notify_document_changed()
        self.context.refresh(rect)


class PickerTool(Tool):
    key = "picker"
    label = "Conta-gotas"
    icon = "picker"
    shortcut = "K"
    hint = "Clique para capturar a cor. Botão direito define a cor secundária."
    group = "desenho"
    cursor_shape = Qt.CursorShape.CrossCursor

    def press(self, event: CanvasEvent) -> None:
        x, y = event.pixel
        if not (0 <= x < self.document.width and 0 <= y < self.document.height):
            return
        red, green, blue, alpha = (int(value) for value in self.document.pixels[y, x])
        picked = QColor(red, green, blue, alpha)
        if event.is_secondary:
            self.settings.secondary = picked
        else:
            self.settings.primary = picked
        self.context.show_hint(f"Cor capturada: {picked.name().upper()}")
        self.context.activate_previous_tool()


class ZoomTool(Tool):
    key = "zoom"
    label = "Lupa"
    icon = "zoom_in"
    shortcut = "Z"
    hint = "Clique para aproximar; botão direito para afastar."
    group = "navegação"

    def press(self, event: CanvasEvent) -> None:
        factor = 1.0 / ZOOM_STEP if event.is_secondary else ZOOM_STEP
        self.context.zoom_at(event.position, factor)

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.PointingHandCursor)


class PanTool(Tool):
    key = "pan"
    label = "Mão"
    icon = "hand"
    shortcut = "Espaço"
    hint = "Arraste para deslocar a imagem. O botão do meio faz o mesmo em qualquer ferramenta."
    group = "navegação"
    cursor_shape = Qt.CursorShape.OpenHandCursor

    def __init__(self, context) -> None:
        super().__init__(context)
        self._anchor: QPointF | None = None

    def press(self, event: CanvasEvent) -> None:
        self._anchor = event.position

    def move(self, event: CanvasEvent) -> None:
        if self._anchor is None:
            return
        # O deslocamento é medido em pixels do documento e convertido pela vista,
        # então o arraste acompanha o cursor em qualquer nível de zoom.
        self.context.pan_by(event.position - self._anchor)

    def release(self, event: CanvasEvent) -> None:
        self._anchor = None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.OpenHandCursor)
