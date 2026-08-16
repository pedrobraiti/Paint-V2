"""A área de desenho: desenha o documento e roteia os gestos para a ferramenta.

O widget não guarda uma cópia da imagem. O ``QImage`` que ele desenha aponta para
o mesmo bloco de memória do array NumPy do documento, então uma pincelada aparece
na tela sem nenhuma conversão no meio — basta invalidar o retângulo alterado.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QTransform,
)
from PySide6.QtWidgets import QWidget

from ..core.document import Document
from ..core.pixels import Rect
from ..core.selection import Selection
from ..tools.base import CanvasEvent, Tool
from ..tools.qt_bridge import document_image
from ..tools.registry import DEFAULT_TOOL_KEY, TOOL_CLASSES
from ..tools.settings import ToolSettings
from .theme import PALETTE

MIN_ZOOM = 0.02
MAX_ZOOM = 32.0
ZOOM_WHEEL_STEP = 1.15
CHECKER_TILE = 12
ANTS_INTERVAL_MS = 90


class CanvasView(QWidget):
    """Widget de edição. Implementa o ``ToolContext`` que as ferramentas usam."""

    cursor_moved = Signal(QPointF)
    cursor_left = Signal()
    zoom_changed = Signal(float)
    document_modified = Signal()
    hint_requested = Signal(str)
    tool_changed = Signal(str)
    tool_shortcut_pressed = Signal(str)
    selection_changed = Signal()

    def __init__(self, settings: ToolSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._settings = settings
        self._document = Document.blank(800, 600)
        self._selection = Selection(self._document.width, self._document.height)
        self._selection_outline: QPainterPath | None = None

        self._zoom = 1.0
        self._origin = QPointF(0.0, 0.0)
        self._cursor_position = QPointF(-1.0, -1.0)
        self._cursor_inside = False

        # Um documento carregado antes de a janela existir seria enquadrado
        # contra um widget de tamanho zero; o reenquadramento fica pendente até
        # o primeiro resize real.
        self._pending_fit = True
        self._panning = False
        self._pan_anchor = QPointF()
        self._space_held = False
        self._active_button = Qt.MouseButton.NoButton

        self._checker = _checker_brush()
        self._ants_phase = 0
        self._ants_timer = QTimer(self)
        self._ants_timer.setInterval(ANTS_INTERVAL_MS)
        self._ants_timer.timeout.connect(self._advance_ants)

        self._tools: dict[str, Tool] = {
            tool_class.key: tool_class(self) for tool_class in TOOL_CLASSES
        }
        # Atalhos de uma letra ficam no canvas, e não em QActions da janela:
        # assim eles não roubam a tecla de quem está digitando com a ferramenta
        # de texto, cujo campo de edição fica em foco no lugar do canvas.
        self._letter_shortcuts = {
            tool_class.shortcut.upper(): tool_class.key
            for tool_class in TOOL_CLASSES
            if len(tool_class.shortcut) == 1
        }
        self._tool_key = DEFAULT_TOOL_KEY
        self._previous_tool_key = DEFAULT_TOOL_KEY
        self._tool.activate()
        self._apply_cursor()

    # ------------------------------------------------------------- documento

    @property
    def document(self) -> Document:
        return self._document

    @property
    def selection(self) -> Selection:
        return self._selection

    @property
    def settings(self) -> ToolSettings:
        return self._settings

    @property
    def zoom(self) -> float:
        return self._zoom

    def set_document(self, document: Document) -> None:
        """Troca o documento em edição e reenquadra a vista."""
        self._tool.commit_pending()
        self._document = document
        self._selection = Selection(document.width, document.height)
        self._selection_outline = None
        self._pending_fit = True
        self.fit_to_view()
        self.document_modified.emit()
        self.selection_changed.emit()
        self.update()

    def sync_after_resize(self) -> None:
        """Reajusta seleção e enquadramento depois de mudar o tamanho da imagem."""
        self._selection = Selection(self._document.width, self._document.height)
        self._selection_outline = None
        self._clamp_origin()
        self.selection_changed.emit()
        self.update()

    # ---------------------------------------------------------- ferramentas

    @property
    def tool_key(self) -> str:
        return self._tool_key

    @property
    def _tool(self) -> Tool:
        return self._tools[self._tool_key]

    def tool(self, key: str | None = None) -> Tool:
        return self._tools[key or self._tool_key]

    def set_tool(self, key: str) -> None:
        if key == self._tool_key or key not in self._tools:
            return
        self._tool.deactivate()
        self._previous_tool_key = self._tool_key
        self._tool_key = key
        self._tool.activate()
        self._apply_cursor()
        self.tool_changed.emit(key)
        self.hint_requested.emit(self._tool.hint)
        self.update()

    def activate_previous_tool(self) -> None:
        if self._previous_tool_key != self._tool_key:
            self.set_tool(self._previous_tool_key)

    def commit_active_tool(self) -> None:
        """Fecha o que estiver em andamento antes de uma ação de menu."""
        self._tool.commit_pending()

    # ------------------------------------------------------ ToolContext extra

    def refresh(self, rect: Rect | None = None) -> None:
        if rect is None:
            self.update()
            return
        self.update(self._document_rect_to_widget(rect))

    def refresh_overlay(self) -> None:
        self.update()

    def notify_document_changed(self) -> None:
        self.document_modified.emit()

    def show_hint(self, message: str) -> None:
        self.hint_requested.emit(message)

    def set_selection_outline(self, outline: QPainterPath | None) -> None:
        self._selection_outline = outline
        self._update_ants_timer()
        self.selection_changed.emit()
        self.update()

    def refresh_selection_outline(self) -> None:
        from ..tools.selection_tools import selection_outline

        self.set_selection_outline(selection_outline(self._selection))

    def canvas_widget(self) -> CanvasView:
        return self

    # ------------------------------------------------------------ navegação

    def document_transform(self) -> QTransform:
        transform = QTransform()
        transform.translate(self._origin.x(), self._origin.y())
        transform.scale(self._zoom, self._zoom)
        return transform

    def document_to_widget(self, x: float, y: float) -> QPointF:
        return QPointF(self._origin.x() + x * self._zoom, self._origin.y() + y * self._zoom)

    def widget_to_document(self, point: QPointF) -> QPointF:
        return QPointF(
            (point.x() - self._origin.x()) / self._zoom,
            (point.y() - self._origin.y()) / self._zoom,
        )

    def set_zoom(self, zoom: float, anchor: QPointF | None = None) -> None:
        """Ajusta o zoom mantendo fixo o ponto sob o cursor (ou o centro)."""
        zoom = float(np.clip(zoom, MIN_ZOOM, MAX_ZOOM))
        if abs(zoom - self._zoom) < 1e-6:
            return
        pivot = anchor or QPointF(self.width() / 2.0, self.height() / 2.0)
        document_pivot = self.widget_to_document(pivot)
        self._zoom = zoom
        self._origin = QPointF(
            pivot.x() - document_pivot.x() * zoom,
            pivot.y() - document_pivot.y() * zoom,
        )
        self._clamp_origin()
        self._tool.on_view_changed()
        self.zoom_changed.emit(self._zoom)
        self.update()

    def zoom_at(self, document_point: QPointF, factor: float) -> None:
        anchor = self.document_to_widget(document_point.x(), document_point.y())
        self.set_zoom(self._zoom * factor, anchor)

    def zoom_in(self) -> None:
        self.set_zoom(self._zoom * ZOOM_WHEEL_STEP)

    def zoom_out(self) -> None:
        self.set_zoom(self._zoom / ZOOM_WHEEL_STEP)

    def zoom_to_actual_size(self) -> None:
        self.set_zoom(1.0)
        self.center_document()

    def fit_to_view(self) -> None:
        """Enquadra a imagem inteira, sem ampliar além do tamanho real."""
        if self._document.width <= 0 or self._document.height <= 0:
            return
        # Antes de a janela aparecer, o tamanho do widget ainda é o provisório do
        # layout: o enquadramento sairia errado, então fica pendente.
        self._pending_fit = not self.isVisible() or self.width() <= 1
        available_width = max(self.width() - 48, 64)
        available_height = max(self.height() - 48, 64)
        zoom = min(
            available_width / self._document.width,
            available_height / self._document.height,
            1.0,
        )
        self._zoom = float(np.clip(zoom, MIN_ZOOM, MAX_ZOOM))
        self.center_document()
        self.zoom_changed.emit(self._zoom)

    def center_document(self) -> None:
        self._origin = QPointF(
            (self.width() - self._document.width * self._zoom) / 2.0,
            (self.height() - self._document.height * self._zoom) / 2.0,
        )
        self._clamp_origin()
        self._tool.on_view_changed()
        self.update()

    def pan_by(self, document_delta: QPointF) -> None:
        self._origin += document_delta * self._zoom
        self._clamp_origin()
        self._tool.on_view_changed()
        self.update()

    def _clamp_origin(self) -> None:
        """Centraliza o que cabe na vista e impede arrastar a imagem para fora.

        Enquanto a imagem couber inteira, ela fica centralizada — inclusive ao
        redimensionar a janela. Ampliada, o arraste é limitado para que a área de
        trabalho nunca fique vazia.
        """
        self._origin = QPointF(
            _clamp_axis(self._origin.x(), self._document.width * self._zoom, self.width()),
            _clamp_axis(self._origin.y(), self._document.height * self._zoom, self.height()),
        )

    # -------------------------------------------------------------- desenho

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(PALETTE.canvas_void))

        target = QRectF(
            self._origin.x(),
            self._origin.y(),
            self._document.width * self._zoom,
            self._document.height * self._zoom,
        )
        painter.fillRect(target, self._checker)
        painter.setRenderHint(
            QPainter.RenderHint.SmoothPixmapTransform, self._zoom < 1.0
        )
        painter.drawImage(target, document_image(self._document))

        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self._paint_border(painter, target)
        self._paint_selection(painter)
        self._tool.paint_overlay(painter, self)
        self._paint_brush_outline(painter)
        painter.end()

    def _paint_border(self, painter: QPainter, target: QRectF) -> None:
        pen = QPen(QColor(PALETTE.border_strong))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(target.adjusted(-0.5, -0.5, 0.5, 0.5))

    def _paint_selection(self, painter: QPainter) -> None:
        if self._selection_outline is None:
            return
        painter.save()
        painter.setTransform(self.document_transform(), True)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        scale = 1.0 / max(self._zoom, 0.05)

        backdrop = QPen(QColor(0, 0, 0, 200))
        backdrop.setWidthF(1.2 * scale)
        painter.setPen(backdrop)
        painter.drawPath(self._selection_outline)

        ants = QPen(QColor(255, 255, 255))
        ants.setWidthF(1.2 * scale)
        ants.setStyle(Qt.PenStyle.CustomDashLine)
        ants.setDashPattern([4.0, 4.0])
        ants.setDashOffset(self._ants_phase)
        painter.setPen(ants)
        painter.drawPath(self._selection_outline)
        painter.restore()

    def _paint_brush_outline(self, painter: QPainter) -> None:
        if not self._cursor_inside or not self._tool.shows_brush_outline:
            return
        radius = max(self._settings.brush_size * self._zoom / 2.0, 3.0)
        center = self.document_to_widget(
            self._cursor_position.x(), self._cursor_position.y()
        )
        painter.setBrush(Qt.BrushStyle.NoBrush)
        outer = QPen(QColor(0, 0, 0, 190))
        outer.setWidthF(2.2)
        painter.setPen(outer)
        painter.drawEllipse(center, radius, radius)
        inner = QPen(QColor(255, 255, 255, 230))
        inner.setWidthF(1.0)
        painter.setPen(inner)
        painter.drawEllipse(center, radius, radius)
        # Um ponto no centro devolve a precisão que o cursor oculto tirou.
        painter.drawPoint(center)

    def _advance_ants(self) -> None:
        self._ants_phase = (self._ants_phase + 1) % 8
        self.update()

    def _update_ants_timer(self) -> None:
        if self._selection_outline is not None and not self._ants_timer.isActive():
            self._ants_timer.start()
        elif self._selection_outline is None and self._ants_timer.isActive():
            self._ants_timer.stop()

    def _document_rect_to_widget(self, rect: Rect) -> QRect:
        x, y, width, height = rect
        top_left = self.document_to_widget(x, y)
        margin = int(self._settings.brush_size * self._zoom) + 4
        return QRect(
            int(top_left.x()) - margin,
            int(top_left.y()) - margin,
            int(width * self._zoom) + margin * 2,
            int(height * self._zoom) + margin * 2,
        )

    # -------------------------------------------------------------- eventos

    def _make_event(self, source, pressure: float = 1.0) -> CanvasEvent:
        position = self.widget_to_document(QPointF(source.position()))
        return CanvasEvent(
            position=position,
            button=source.button() if hasattr(source, "button") else Qt.MouseButton.NoButton,
            buttons=source.buttons(),
            modifiers=source.modifiers(),
            pressure=pressure,
        )

    def mousePressEvent(self, event) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        if event.button() == Qt.MouseButton.MiddleButton or self._space_held:
            self._panning = True
            self._pan_anchor = QPointF(event.position())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        self._active_button = event.button()
        self._tool.press(self._make_event(event))

    def mouseMoveEvent(self, event) -> None:
        position = self.widget_to_document(QPointF(event.position()))
        self._cursor_position = position
        self.cursor_moved.emit(position)

        if self._panning:
            delta = QPointF(event.position()) - self._pan_anchor
            self._pan_anchor = QPointF(event.position())
            self._origin += delta
            self._clamp_origin()
            self._tool.on_view_changed()
            self.update()
            return

        self._tool.move(self._make_event(event))
        if self._tool.shows_brush_outline:
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._panning:
            self._panning = False
            self._apply_cursor()
            return
        self._tool.release(self._make_event(event))
        self._active_button = Qt.MouseButton.NoButton

    def mouseDoubleClickEvent(self, event) -> None:
        self._tool.double_click(self._make_event(event))

    def tabletEvent(self, event) -> None:
        """Caneta: usa a pressão real para modular tamanho e fluxo do traço."""
        pressure = float(event.pressure()) or 1.0
        canvas_event = CanvasEvent(
            position=self.widget_to_document(QPointF(event.position())),
            button=event.button(),
            buttons=event.buttons(),
            modifiers=event.modifiers(),
            pressure=pressure,
        )
        event_type = event.type()
        if event_type == event.Type.TabletPress:
            self._tool.press(canvas_event)
        elif event_type == event.Type.TabletMove:
            self._cursor_position = canvas_event.position
            self.cursor_moved.emit(canvas_event.position)
            self._tool.move(canvas_event)
        elif event_type == event.Type.TabletRelease:
            self._tool.release(canvas_event)
        event.accept()

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if not delta:
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = ZOOM_WHEEL_STEP if delta > 0 else 1.0 / ZOOM_WHEEL_STEP
            self.set_zoom(self._zoom * factor, QPointF(event.position()))
            return
        step = 60 if delta > 0 else -60
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._origin += QPointF(step, 0)
        else:
            self._origin += QPointF(0, step)
        self._clamp_origin()
        self._tool.on_view_changed()
        self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        if self._tool.key_press(event.key(), event.modifiers()):
            return
        if not event.modifiers():
            letter = event.text().upper()
            if letter == "X":
                self._settings.swap_colors()
                return
            tool_key = self._letter_shortcuts.get(letter)
            if tool_key is not None:
                self.set_tool(tool_key)
                self.tool_shortcut_pressed.emit(tool_key)
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self._space_held = False
            self._apply_cursor()
            return
        super().keyReleaseEvent(event)

    def enterEvent(self, event) -> None:
        self._cursor_inside = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._cursor_inside = False
        self.cursor_left.emit()
        self.update()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._pending_fit:
            self.fit_to_view()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._pending_fit and self.isVisible() and self.width() > 1:
            self.fit_to_view()
            return
        self._clamp_origin()
        self._tool.on_view_changed()

    def _apply_cursor(self) -> None:
        if self._tool.shows_brush_outline:
            self.setCursor(Qt.CursorShape.BlankCursor)
            return
        self.setCursor(self._tool.cursor())


def _clamp_axis(origin: float, scaled_size: float, viewport_size: float) -> float:
    if scaled_size <= viewport_size:
        return (viewport_size - scaled_size) / 2.0
    return float(np.clip(origin, viewport_size - scaled_size, 0.0))


def _checker_brush() -> QBrush:
    """Xadrez que revela a transparência por baixo da imagem."""
    pixmap = QPixmap(CHECKER_TILE * 2, CHECKER_TILE * 2)
    pixmap.fill(QColor(PALETTE.checker_dark))
    painter = QPainter(pixmap)
    painter.fillRect(0, 0, CHECKER_TILE, CHECKER_TILE, QColor(PALETTE.checker_light))
    painter.fillRect(
        CHECKER_TILE, CHECKER_TILE, CHECKER_TILE, CHECKER_TILE, QColor(PALETTE.checker_light)
    )
    painter.end()
    return QBrush(pixmap)
