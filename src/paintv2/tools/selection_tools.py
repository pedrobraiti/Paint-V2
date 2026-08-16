"""Seleção retangular e à mão livre, com mover, copiar e colar.

Ao arrastar uma seleção, o documento só é alterado no fim: durante o arraste os
pixels flutuam na sobreposição. Assim o movimento inteiro — apagar a origem e
colar no destino — entra no histórico como **um** passo de desfazer, que é o que
o usuário espera ao apertar Ctrl+Z depois de arrastar algo sem querer.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen

from ..core.pixels import (
    clip_rect,
    composite_over,
    to_float,
    to_uint8,
    union_rect,
    view,
)
from .base import CanvasEvent, Tool, ToolContext
from .qt_bridge import array_to_image, rasterize_path

MOVE_LABEL = "Mover seleção"
PASTE_LABEL = "Colar"


class FloatingPixels:
    """Recorte que está sendo arrastado por cima do documento."""

    def __init__(self, pixels: np.ndarray, mask: np.ndarray, origin: tuple[int, int]) -> None:
        self.pixels = pixels
        self.mask = mask
        self.origin = origin
        self.offset = [0, 0]
        self.source_backup: np.ndarray | None = None
        self.source_rect: tuple[int, int, int, int] | None = None

    @property
    def destination(self) -> tuple[int, int, int, int]:
        height, width = self.pixels.shape[:2]
        return (
            self.origin[0] + self.offset[0],
            self.origin[1] + self.offset[1],
            width,
            height,
        )


class SelectionTool(Tool):
    """Base comum ao retângulo e ao laço."""

    group = "seleção"
    options = ()
    cursor_shape = Qt.CursorShape.CrossCursor
    freehand = False

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self._anchor: QPointF | None = None
        self._current: QPointF | None = None
        self._points: list[QPointF] = []
        self._floating: FloatingPixels | None = None
        self._move_anchor: QPointF | None = None

    # ------------------------------------------------------------------ ciclo

    def activate(self) -> None:
        self._publish_outline()

    def deactivate(self) -> None:
        self.commit_pending()

    def commit_pending(self) -> None:
        if self._floating is not None:
            self._commit_floating()
        self._anchor = None
        self._current = None
        self._points = []
        self.context.refresh_overlay()

    # ---------------------------------------------------------------- eventos

    def press(self, event: CanvasEvent) -> None:
        if event.button != Qt.MouseButton.LeftButton:
            return

        x, y = event.pixel
        if self._floating is not None:
            if _inside(self._floating.destination, x, y):
                self._move_anchor = event.position
                return
            self._commit_floating()

        if self.context.selection.contains(x, y):
            self._lift(copy=event.from_center)
            self._move_anchor = event.position
            return

        self._anchor = event.position
        self._current = event.position
        self._points = [event.position]

    def move(self, event: CanvasEvent) -> None:
        if self._move_anchor is not None and self._floating is not None:
            delta = event.position - self._move_anchor
            self._floating.offset[0] += int(round(delta.x()))
            self._floating.offset[1] += int(round(delta.y()))
            self._move_anchor = event.position
            self.context.refresh()
            return

        if self._anchor is None:
            return
        self._current = event.position
        if self.freehand:
            self._points.append(event.position)
        self.context.refresh_overlay()

    def release(self, event: CanvasEvent) -> None:
        if self._move_anchor is not None:
            self._move_anchor = None
            return
        if self._anchor is None:
            return

        self._current = event.position
        self._apply_new_selection()
        self._anchor = None
        self._points = []
        self.context.refresh_overlay()

    def key_press(self, key: int, modifiers: Qt.KeyboardModifier) -> bool:
        if key == Qt.Key.Key_Escape:
            self.cancel_floating()
            self.context.selection.clear()
            self._publish_outline()
            self.context.refresh()
            return True
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.commit_pending()
            self.context.refresh()
            return True
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selection()
            return True
        return False

    def cursor(self) -> QCursor:
        if self._floating is not None:
            return QCursor(Qt.CursorShape.SizeAllCursor)
        return QCursor(self.cursor_shape)

    # ------------------------------------------------------------ sobreposição

    def paint_overlay(self, painter: QPainter, view_widget) -> None:
        if self._floating is not None:
            self._paint_floating(painter, view_widget)
        if self._anchor is None or self._current is None:
            return
        painter.save()
        painter.setTransform(view_widget.document_transform(), True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(_marching_pen(1.0 / max(view_widget.zoom, 0.05)))
        painter.drawPath(self._draft_path())
        painter.restore()

    def _paint_floating(self, painter: QPainter, view_widget) -> None:
        floating = self._floating
        assert floating is not None
        x, y, width, height = floating.destination
        painter.save()
        painter.setTransform(view_widget.document_transform(), True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.drawImage(QRectF(x, y, width, height), array_to_image(floating.pixels))
        painter.setPen(_marching_pen(1.0 / max(view_widget.zoom, 0.05)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(x, y, width, height))
        painter.restore()

    # --------------------------------------------------------------- seleção

    def _draft_path(self) -> QPainterPath:
        path = QPainterPath()
        if self.freehand and len(self._points) > 1:
            path.moveTo(self._points[0])
            for point in self._points[1:]:
                path.lineTo(point)
            path.closeSubpath()
        elif self._anchor is not None and self._current is not None:
            path.addRect(QRectF(self._anchor, self._current).normalized())
        return path

    def _apply_new_selection(self) -> None:
        selection = self.context.selection
        if self.freehand:
            if len(self._points) < 3:
                selection.clear()
            else:
                mask = rasterize_path(
                    self._draft_path(), self.document.width, self.document.height
                )
                selection.set_mask(mask)
        else:
            rect = QRectF(self._anchor, self._current).normalized()
            if rect.width() < 1 or rect.height() < 1:
                selection.clear()
            else:
                selection.set_rect(
                    (
                        int(round(rect.left())),
                        int(round(rect.top())),
                        int(round(rect.width())),
                        int(round(rect.height())),
                    )
                )
        self._publish_outline()

    def _publish_outline(self) -> None:
        self.context.set_selection_outline(selection_outline(self.context.selection))

    # -------------------------------------------------------------- flutuante

    def _lift(self, copy: bool = False) -> None:
        """Recorta a seleção do documento para que ela possa ser arrastada."""
        selection = self.context.selection
        bounds = selection.bounds
        if bounds is None or selection.mask is None:
            return

        region = view(self.document.pixels, bounds).copy()
        mask = view(selection.mask, bounds).copy()
        region[~mask] = 0

        floating = FloatingPixels(region, mask, (bounds[0], bounds[1]))
        if not copy:
            floating.source_backup = view(self.document.pixels, bounds).copy()
            floating.source_rect = bounds
            view(self.document.pixels, bounds)[mask] = 0
        self._floating = floating
        self.context.refresh()

    def _commit_floating(self) -> None:
        floating, self._floating = self._floating, None
        if floating is None:
            return

        destination = clip_rect(
            floating.destination, self.document.width, self.document.height
        )
        affected = union_rect(destination, floating.source_rect)
        if affected is None:
            self._restore_source(floating)
            return

        before = self.document.snapshot_region(affected)
        if before is None:
            return
        if floating.source_backup is not None and floating.source_rect is not None:
            # O recorte já saiu do documento; recompor o estado original nessa
            # cópia é o que permite registrar tudo como um único passo.
            source_x = floating.source_rect[0] - affected[0]
            source_y = floating.source_rect[1] - affected[1]
            before[
                source_y : source_y + floating.source_rect[3],
                source_x : source_x + floating.source_rect[2],
            ] = floating.source_backup

        if destination is not None:
            self._blit(floating, destination)
        self.document.commit_patch(MOVE_LABEL, affected, before)
        self.context.notify_document_changed()

        self.context.selection.set_rect(destination or (0, 0, 0, 0))
        self._publish_outline()
        self.context.refresh()

    def _blit(self, floating: FloatingPixels, destination) -> None:
        target_x, target_y, width, height = destination
        origin_x, origin_y, _, _ = floating.destination
        crop_x = target_x - origin_x
        crop_y = target_y - origin_y
        patch = floating.pixels[crop_y : crop_y + height, crop_x : crop_x + width]

        target = view(self.document.pixels, destination)
        source = to_float(patch)
        composed = composite_over(to_float(target), source[..., :3], source[..., 3])
        target[:] = to_uint8(composed)

    def _restore_source(self, floating: FloatingPixels) -> None:
        if floating.source_backup is not None and floating.source_rect is not None:
            view(self.document.pixels, floating.source_rect)[:] = floating.source_backup

    def cancel_floating(self) -> None:
        """Descarta o recorte em voo e devolve os pixels ao lugar de origem."""
        if self._floating is None:
            return
        self._restore_source(self._floating)
        self._floating = None
        self.context.refresh()

    # ---------------------------------------------------- ações do menu Editar

    def has_floating(self) -> bool:
        return self._floating is not None

    def delete_selection(self) -> None:
        """Apaga o conteúdo da seleção, deixando transparente."""
        if self._floating is not None:
            self._floating = None
            self.context.refresh()
            self.context.notify_document_changed()
            return

        selection = self.context.selection
        bounds = selection.bounds
        if bounds is None or selection.mask is None:
            return
        before = self.document.snapshot_region(bounds)
        if before is None:
            return
        view(self.document.pixels, bounds)[view(selection.mask, bounds)] = 0
        self.document.commit_patch("Apagar seleção", bounds, before)
        self.context.notify_document_changed()
        self.context.refresh(bounds)

    def copied_pixels(self) -> np.ndarray | None:
        """Pixels da seleção (ou do recorte flutuante) para a área de transferência."""
        if self._floating is not None:
            return self._floating.pixels.copy()
        selection = self.context.selection
        bounds = selection.bounds
        if bounds is None or selection.mask is None:
            return None
        region = view(self.document.pixels, bounds).copy()
        region[~view(selection.mask, bounds)] = 0
        return region

    def begin_paste(self, pixels: np.ndarray, origin: tuple[int, int] = (0, 0)) -> None:
        """Coloca pixels colados em estado flutuante, prontos para posicionar."""
        self.commit_pending()
        mask = pixels[..., 3] > 0
        self._floating = FloatingPixels(np.ascontiguousarray(pixels), mask, origin)
        height, width = pixels.shape[:2]
        self.context.selection.set_rect((origin[0], origin[1], width, height))
        self._publish_outline()
        self.context.show_hint("Arraste para posicionar e pressione Enter para fixar.")
        self.context.refresh()


class SelectRectangleTool(SelectionTool):
    key = "select_rect"
    label = "Seleção retangular"
    icon = "select_rect"
    shortcut = "M"
    hint = "Arraste para selecionar; arraste dentro para mover. Ctrl+arraste duplica."


class SelectLassoTool(SelectionTool):
    key = "select_lasso"
    label = "Seleção livre"
    icon = "select_lasso"
    shortcut = "N"
    hint = "Contorne a área à mão livre; solte para fechar a seleção."
    freehand = True


def selection_outline(selection) -> QPainterPath | None:
    """Contorno da seleção para as formiguinhas da sobreposição."""
    if not selection.is_active or selection.mask is None:
        return None
    mask = selection.mask
    path = QPainterPath()
    padded = np.pad(mask, 1, constant_values=False)

    horizontal = np.diff(padded.astype(np.int8), axis=1)
    vertical = np.diff(padded.astype(np.int8), axis=0)

    for row, column in zip(*np.nonzero(horizontal), strict=True):
        path.moveTo(column, row - 1)
        path.lineTo(column, row)
    for row, column in zip(*np.nonzero(vertical), strict=True):
        path.moveTo(column - 1, row)
        path.lineTo(column, row)
    return path


def _marching_pen(scale: float) -> QPen:
    pen = QPen(QColor(255, 255, 255))
    pen.setWidthF(1.4 * scale)
    pen.setStyle(Qt.PenStyle.DashLine)
    pen.setDashPattern([4.0, 4.0])
    pen.setCosmetic(False)
    return pen


def _inside(rect, x: int, y: int) -> bool:
    left, top, width, height = rect
    return left <= x < left + width and top <= y < top + height
