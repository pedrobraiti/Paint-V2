"""Ferramenta de texto com edição direto sobre a tela.

O texto é digitado num campo transparente posicionado por cima do canvas, com a
mesma fonte e o mesmo tamanho que terá na imagem — o que se vê digitando é o que
fica gravado. Os pixels só mudam quando a caixa é confirmada.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPen, QTextOption
from PySide6.QtWidgets import QTextEdit

from .base import CanvasEvent, Tool, ToolContext
from .qt_bridge import painter_for

MIN_BOX_WIDTH = 160
MIN_BOX_HEIGHT = 48
BOX_PADDING = 6
MARGIN = 4
MAX_TEXT_HEIGHT = 20_000.0


class TextTool(Tool):
    key = "text"
    label = "Texto"
    icon = "text"
    shortcut = "T"
    hint = "Clique para posicionar e digite. Ctrl+Enter grava, Esc cancela."
    group = "desenho"
    options = ("font_family", "font_size", "font_style")
    cursor_shape = Qt.CursorShape.IBeamCursor

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self._editor: QTextEdit | None = None
        self._origin: tuple[float, float] | None = None
        self._box_size = (MIN_BOX_WIDTH, MIN_BOX_HEIGHT)
        self._color = QColor(Qt.GlobalColor.black)

    # ---------------------------------------------------------------- eventos

    def press(self, event: CanvasEvent) -> None:
        if event.button != Qt.MouseButton.LeftButton:
            return
        self.commit_pending()
        self._origin = (event.x, event.y)
        self._color = self.settings.primary
        self._open_editor()

    def key_press(self, key: int, modifiers: Qt.KeyboardModifier) -> bool:
        if self._editor is None:
            return False
        if key == Qt.Key.Key_Escape:
            self._close_editor()
            self.context.refresh()
            return True
        return False

    def deactivate(self) -> None:
        self.commit_pending()

    def on_view_changed(self) -> None:
        self._sync_editor_geometry()

    # ----------------------------------------------------------------- editor

    def _open_editor(self) -> None:
        canvas = self.context.canvas_widget()
        editor = QTextEdit(canvas)
        editor.setFrameShape(QTextEdit.Shape.NoFrame)
        editor.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        editor.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        editor.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        editor.setStyleSheet(
            "QTextEdit {"
            "background: rgba(0, 0, 0, 40);"
            f"color: {self._color.name()};"
            "border: 1px dashed rgba(255, 255, 255, 140);"
            f"padding: {BOX_PADDING}px;"
            "}"
        )
        editor.setAcceptRichText(False)
        editor.textChanged.connect(self._grow_to_fit)

        self._editor = editor
        self._sync_editor_geometry()
        editor.show()
        editor.setFocus(Qt.FocusReason.MouseFocusReason)
        self.context.show_hint(self.hint)

    def _document_font(self) -> QFont:
        font = QFont(self.settings.font_family)
        font.setPixelSize(max(4, self.settings.font_size))
        font.setBold(self.settings.font_bold)
        font.setItalic(self.settings.font_italic)
        return font

    def _sync_editor_geometry(self) -> None:
        if self._editor is None or self._origin is None:
            return
        view = self.context.canvas_widget()
        zoom = view.zoom
        top_left = view.document_to_widget(*self._origin)

        font = self._document_font()
        font.setPixelSize(max(4, int(round(self.settings.font_size * zoom))))
        self._editor.setFont(font)
        self._editor.setGeometry(
            QRect(
                int(top_left.x()),
                int(top_left.y()),
                int(self._box_size[0] * zoom),
                int(self._box_size[1] * zoom),
            )
        )

    def _grow_to_fit(self) -> None:
        """Cresce a caixa conforme o texto, sem nunca encolher abaixo do mínimo."""
        if self._editor is None:
            return
        zoom = max(self.context.canvas_widget().zoom, 0.01)
        document_height = self._editor.document().size().height() / zoom
        needed = max(MIN_BOX_HEIGHT, document_height + BOX_PADDING * 2)
        if abs(needed - self._box_size[1]) > 1.0:
            self._box_size = (self._box_size[0], needed)
            self._sync_editor_geometry()

    def _close_editor(self) -> str:
        if self._editor is None:
            return ""
        text = self._editor.toPlainText()
        self._editor.textChanged.disconnect(self._grow_to_fit)
        self._editor.deleteLater()
        self._editor = None
        self._box_size = (MIN_BOX_WIDTH, MIN_BOX_HEIGHT)
        return text

    # ------------------------------------------------------------------ grava

    def commit_pending(self) -> None:
        origin = self._origin
        text = self._close_editor()
        self._origin = None
        if not text.strip() or origin is None:
            return
        self._render(origin, text)

    def _render(self, origin: tuple[float, float], text: str) -> None:
        font = self._document_font()
        box = QRectF(
            origin[0] + BOX_PADDING,
            origin[1] + BOX_PADDING,
            max(MIN_BOX_WIDTH, self._box_size[0]) - BOX_PADDING * 2,
            MAX_TEXT_HEIGHT,
        )

        # Medir com QFontMetricsF em vez de um QPainter: fora do paintEvent não
        # existe superfície válida para pintar, e a métrica basta para o recorte.
        occupied = QFontMetricsF(font).boundingRect(box, Qt.TextFlag.TextWordWrap, text)
        rect = (
            int(math.floor(occupied.left())) - MARGIN,
            int(math.floor(occupied.top())) - MARGIN,
            int(math.ceil(occupied.width())) + MARGIN * 2,
            int(math.ceil(occupied.height())) + MARGIN * 2,
        )
        before = self.document.snapshot_region(rect)
        if before is None:
            return

        with painter_for(
            self.document, self.context.selection, self.settings.antialias
        ) as painter:
            painter.setFont(font)
            painter.setPen(QPen(self._color))
            painter.drawText(box, Qt.TextFlag.TextWordWrap, text)

        self.document.commit_patch(self.label, rect, before)
        self.context.notify_document_changed()
        self.context.refresh()
