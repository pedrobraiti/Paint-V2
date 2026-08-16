"""Linha, curva e formas geométricas.

Enquanto o usuário arrasta, a forma só existe como sobreposição na tela; os
pixels do documento são tocados uma única vez, na hora de soltar o botão. Isso
mantém o arraste fluido em imagens grandes e deixa um único passo no desfazer.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen

from .base import CanvasEvent, Tool, ToolContext
from .qt_bridge import bounding_rect, painter_for
from .settings import SHAPE_FILL_NONE, SHAPE_FILL_PRIMARY
from .shapes import build_shape_path

ANGLE_SNAP_DEGREES = 15.0


class _VectorTool(Tool):
    """Base das ferramentas que desenham um caminho vetorial."""

    group = "formas"
    cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self._start: QPointF | None = None
        self._end: QPointF | None = None
        self._secondary = False

    # ------------------------------------------------------------ subclasses

    def build_path(self) -> QPainterPath | None:
        raise NotImplementedError

    def is_filled(self) -> bool:
        return False

    # --------------------------------------------------------------- eventos

    def press(self, event: CanvasEvent) -> None:
        if event.button not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        self._secondary = event.is_secondary
        self._start = event.position
        self._end = event.position
        self.context.refresh_overlay()

    def move(self, event: CanvasEvent) -> None:
        if self._start is None:
            return
        self._end = self._adjust(event)
        self.context.refresh_overlay()

    def release(self, event: CanvasEvent) -> None:
        if self._start is None:
            return
        self._end = self._adjust(event)
        self.commit_pending()

    def commit_pending(self) -> None:
        path = self.build_path()
        self._start = None
        self._end = None
        if path is None or path.isEmpty():
            self.context.refresh_overlay()
            return
        self._render(path)

    def paint_overlay(self, painter: QPainter, view) -> None:
        path = self.build_path()
        if path is None or path.isEmpty():
            return
        painter.save()
        painter.setTransform(view.document_transform(), True)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, self.settings.antialias)
        self._configure(painter)
        painter.drawPath(path)
        painter.restore()

    # -------------------------------------------------------------- desenho

    def _configure(self, painter: QPainter) -> None:
        stroke_color = self._stroke_color()
        pen = QPen(stroke_color)
        pen.setWidthF(float(self.settings.line_width))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        if self.is_filled() and self.settings.shape_fill != SHAPE_FILL_NONE:
            painter.setBrush(QBrush(self._fill_color()))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)

    def _stroke_color(self) -> QColor:
        return self.settings.secondary if self._secondary else self.settings.primary

    def _fill_color(self) -> QColor:
        wants_primary = self.settings.shape_fill == SHAPE_FILL_PRIMARY
        if self._secondary:
            return self.settings.secondary if wants_primary else self.settings.primary
        return self.settings.primary if wants_primary else self.settings.secondary

    def _render(self, path: QPainterPath) -> None:
        rect = bounding_rect(path, self.settings.line_width + 2.0)
        before = self.document.snapshot_region(rect)
        if before is None:
            return
        painter = painter_for(self.document, self.context.selection, self.settings.antialias)
        self._configure(painter)
        painter.drawPath(path)
        painter.end()
        self.document.commit_patch(self.label, rect, before)
        self.context.notify_document_changed()
        self.context.refresh()

    def _adjust(self, event: CanvasEvent) -> QPointF:
        return event.position


class LineTool(_VectorTool):
    key = "line"
    label = "Linha"
    icon = "line"
    shortcut = "L"
    hint = "Arraste para traçar. Shift trava o ângulo em múltiplos de 15°."
    options = ("line_width", "antialias")

    def build_path(self) -> QPainterPath | None:
        if self._start is None or self._end is None or self._start == self._end:
            return None
        path = QPainterPath(self._start)
        path.lineTo(self._end)
        return path

    def _adjust(self, event: CanvasEvent) -> QPointF:
        if not event.constrained or self._start is None:
            return event.position
        return _snap_angle(self._start, event.position)


class CurveTool(_VectorTool):
    """Curva em três tempos, como no Paint: traça a reta e depois a entorta duas vezes."""

    key = "curve"
    label = "Curva"
    icon = "curve"
    shortcut = "C"
    hint = "Arraste a reta e depois arraste sobre ela até duas vezes para curvá-la."
    options = ("line_width", "antialias")

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self._stage = 0
        self._control_one: QPointF | None = None
        self._control_two: QPointF | None = None

    def press(self, event: CanvasEvent) -> None:
        if self._stage == 0:
            super().press(event)
            return
        if event.button not in (Qt.MouseButton.LeftButton, Qt.MouseButton.RightButton):
            return
        self._update_control(event.position)

    def move(self, event: CanvasEvent) -> None:
        if self._stage == 0:
            super().move(event)
            return
        if event.buttons & (Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton):
            self._update_control(event.position)

    def release(self, event: CanvasEvent) -> None:
        if self._stage == 0:
            if self._start is None:
                return
            self._end = self._adjust(event)
            self._reset_controls()
            self._stage = 1
            self.context.show_hint("Arraste sobre a linha para curvar (até 2 vezes).")
            self.context.refresh_overlay()
            return

        self._stage += 1
        if self._stage > 2:
            self.commit_pending()

    def key_press(self, key: int, modifiers: Qt.KeyboardModifier) -> bool:
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
            self.commit_pending()
            return True
        return False

    def commit_pending(self) -> None:
        path = self.build_path()
        self._stage = 0
        self._start = self._end = None
        self._control_one = self._control_two = None
        if path is None or path.isEmpty():
            self.context.refresh_overlay()
            return
        self._render(path)

    def build_path(self) -> QPainterPath | None:
        if self._start is None or self._end is None or self._start == self._end:
            return None
        path = QPainterPath(self._start)
        if self._control_one is None or self._control_two is None:
            path.lineTo(self._end)
        else:
            path.cubicTo(self._control_one, self._control_two, self._end)
        return path

    def _reset_controls(self) -> None:
        assert self._start is not None and self._end is not None
        delta = self._end - self._start
        self._control_one = self._start + delta / 3.0
        self._control_two = self._start + delta * (2.0 / 3.0)

    def _update_control(self, position: QPointF) -> None:
        if self._stage == 1:
            self._control_one = position
        else:
            self._control_two = position
        self.context.refresh_overlay()

    def _adjust(self, event: CanvasEvent) -> QPointF:
        if not event.constrained or self._start is None:
            return event.position
        return _snap_angle(self._start, event.position)


class ShapeTool(_VectorTool):
    key = "shape"
    label = "Formas"
    icon = "shapes"
    shortcut = "R"
    hint = "Shift mantém a proporção; Ctrl desenha a partir do centro."
    options = ("shape_kind", "line_width", "shape_fill", "antialias")

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self._from_center = False

    def is_filled(self) -> bool:
        return True

    def build_path(self) -> QPainterPath | None:
        if self._start is None or self._end is None:
            return None
        rect = self._rect()
        if rect.width() < 1.0 and rect.height() < 1.0:
            return None
        return build_shape_path(self.settings.shape_kind, rect)

    def _rect(self) -> QRectF:
        assert self._start is not None and self._end is not None
        if not self._from_center:
            return QRectF(self._start, self._end).normalized()
        offset_x = self._end.x() - self._start.x()
        offset_y = self._end.y() - self._start.y()
        return QRectF(
            self._start.x() - offset_x,
            self._start.y() - offset_y,
            offset_x * 2.0,
            offset_y * 2.0,
        ).normalized()

    def _adjust(self, event: CanvasEvent) -> QPointF:
        self._from_center = event.from_center
        if self._start is None:
            return event.position
        if not event.constrained:
            return event.position
        offset_x = event.position.x() - self._start.x()
        offset_y = event.position.y() - self._start.y()
        side = max(abs(offset_x), abs(offset_y))
        return QPointF(
            self._start.x() + math.copysign(side, offset_x or 1.0),
            self._start.y() + math.copysign(side, offset_y or 1.0),
        )


def _snap_angle(origin: QPointF, position: QPointF) -> QPointF:
    """Prende o ponto ao múltiplo de 15° mais próximo em relação à origem."""
    delta = position - origin
    length = math.hypot(delta.x(), delta.y())
    if length < 1e-6:
        return position
    step = math.radians(ANGLE_SNAP_DEGREES)
    angle = round(math.atan2(delta.y(), delta.x()) / step) * step
    return QPointF(
        origin.x() + length * math.cos(angle), origin.y() + length * math.sin(angle)
    )
