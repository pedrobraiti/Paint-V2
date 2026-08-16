"""Estado compartilhado entre as ferramentas.

Tamanho, ponta, cores e intensidades vivem aqui, e não dentro de cada ferramenta,
porque o usuário espera que ajustar o tamanho no pincel valha também para o
borracha, para a saturação e para o blend. Uma única fonte da verdade evita que a
barra de opções e as ferramentas discordem entre si.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor

from ..core.brush_modes import MODE_DEFINITIONS
from ..core.brush_tips import DEFAULT_TIP_KEY, MAX_SIZE, MIN_SIZE

DEFAULT_BRUSH_SIZE = 14
BRUSH_SLIDER_MAX = 1000
"""Fim da rampa do controle deslizante.

Passar disso na rampa tornaria cada pixel dela um salto grande demais para
ajuste fino; quem precisa de mais digita o número no campo ao lado, que aceita
até ``MAX_SIZE``."""
DEFAULT_TOLERANCE = 18
DEFAULT_LINE_WIDTH = 3
DEFAULT_FONT_SIZE = 24
DEFAULT_SPRAY_RATE_MS = 30

SHAPE_FILL_NONE = "none"
SHAPE_FILL_SECONDARY = "secondary"
SHAPE_FILL_PRIMARY = "primary"


class ToolSettings(QObject):
    """Preferências de desenho, com sinal único para a interface reagir."""

    changed = Signal()
    colors_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._primary = QColor(255, 159, 69)
        self._secondary = QColor(255, 255, 255)
        self._brush_size = DEFAULT_BRUSH_SIZE
        self._tip_key = DEFAULT_TIP_KEY
        self._opacity = 100
        self._tolerance = DEFAULT_TOLERANCE
        self._fill_contiguous = True
        self._erase_to_transparent = False
        self._antialias = True
        self._shape_kind = "rectangle"
        self._shape_fill = SHAPE_FILL_NONE
        self._line_width = DEFAULT_LINE_WIDTH
        self._font_family = "Segoe UI"
        self._font_size = DEFAULT_FONT_SIZE
        self._font_bold = False
        self._font_italic = False
        self._mode_amounts = {
            definition.key: definition.amount_default for definition in MODE_DEFINITIONS
        }
        self._recent_colors: list[QColor] = []

    # ------------------------------------------------------------------- cores

    @property
    def primary(self) -> QColor:
        return QColor(self._primary)

    @primary.setter
    def primary(self, color: QColor) -> None:
        if color.isValid() and color != self._primary:
            self._primary = QColor(color)
            self._remember_color(color)
            self.colors_changed.emit()
            self.changed.emit()

    @property
    def secondary(self) -> QColor:
        return QColor(self._secondary)

    @secondary.setter
    def secondary(self, color: QColor) -> None:
        if color.isValid() and color != self._secondary:
            self._secondary = QColor(color)
            self._remember_color(color)
            self.colors_changed.emit()
            self.changed.emit()

    def swap_colors(self) -> None:
        self._primary, self._secondary = self._secondary, self._primary
        self.colors_changed.emit()
        self.changed.emit()

    @property
    def recent_colors(self) -> list[QColor]:
        return list(self._recent_colors)

    def _remember_color(self, color: QColor) -> None:
        normalized = QColor(color)
        self._recent_colors = [c for c in self._recent_colors if c != normalized]
        self._recent_colors.insert(0, normalized)
        del self._recent_colors[12:]

    # ---------------------------------------------------------------- pincéis

    @property
    def brush_size(self) -> int:
        return self._brush_size

    @brush_size.setter
    def brush_size(self, value: int) -> None:
        value = max(int(MIN_SIZE), min(int(value), int(MAX_SIZE)))
        if value != self._brush_size:
            self._brush_size = value
            self.changed.emit()

    @property
    def tip_key(self) -> str:
        return self._tip_key

    @tip_key.setter
    def tip_key(self, value: str) -> None:
        if value != self._tip_key:
            self._tip_key = value
            self.changed.emit()

    @property
    def opacity(self) -> int:
        return self._opacity

    @opacity.setter
    def opacity(self, value: int) -> None:
        value = max(1, min(int(value), 100))
        if value != self._opacity:
            self._opacity = value
            self.changed.emit()

    def amount(self, mode_key: str) -> int:
        """Intensidade guardada para um efeito (cada modo tem a sua)."""
        return self._mode_amounts.get(mode_key, 50)

    def set_amount(self, mode_key: str, value: int) -> None:
        if self._mode_amounts.get(mode_key) != value:
            self._mode_amounts[mode_key] = int(value)
            self.changed.emit()

    # -------------------------------------------------------------- balde etc.

    @property
    def tolerance(self) -> int:
        return self._tolerance

    @tolerance.setter
    def tolerance(self, value: int) -> None:
        value = max(0, min(int(value), 100))
        if value != self._tolerance:
            self._tolerance = value
            self.changed.emit()

    @property
    def fill_contiguous(self) -> bool:
        return self._fill_contiguous

    @fill_contiguous.setter
    def fill_contiguous(self, value: bool) -> None:
        if bool(value) != self._fill_contiguous:
            self._fill_contiguous = bool(value)
            self.changed.emit()

    @property
    def erase_to_transparent(self) -> bool:
        return self._erase_to_transparent

    @erase_to_transparent.setter
    def erase_to_transparent(self, value: bool) -> None:
        if bool(value) != self._erase_to_transparent:
            self._erase_to_transparent = bool(value)
            self.changed.emit()

    @property
    def antialias(self) -> bool:
        return self._antialias

    @antialias.setter
    def antialias(self, value: bool) -> None:
        if bool(value) != self._antialias:
            self._antialias = bool(value)
            self.changed.emit()

    # ----------------------------------------------------------------- formas

    @property
    def shape_kind(self) -> str:
        return self._shape_kind

    @shape_kind.setter
    def shape_kind(self, value: str) -> None:
        if value != self._shape_kind:
            self._shape_kind = value
            self.changed.emit()

    @property
    def shape_fill(self) -> str:
        return self._shape_fill

    @shape_fill.setter
    def shape_fill(self, value: str) -> None:
        if value != self._shape_fill:
            self._shape_fill = value
            self.changed.emit()

    @property
    def line_width(self) -> int:
        return self._line_width

    @line_width.setter
    def line_width(self, value: int) -> None:
        value = max(1, min(int(value), 100))
        if value != self._line_width:
            self._line_width = value
            self.changed.emit()

    # ------------------------------------------------------------------ texto

    @property
    def font_family(self) -> str:
        return self._font_family

    @font_family.setter
    def font_family(self, value: str) -> None:
        if value != self._font_family:
            self._font_family = value
            self.changed.emit()

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, value: int) -> None:
        value = max(4, min(int(value), 400))
        if value != self._font_size:
            self._font_size = value
            self.changed.emit()

    @property
    def font_bold(self) -> bool:
        return self._font_bold

    @font_bold.setter
    def font_bold(self, value: bool) -> None:
        if bool(value) != self._font_bold:
            self._font_bold = bool(value)
            self.changed.emit()

    @property
    def font_italic(self) -> bool:
        return self._font_italic

    @font_italic.setter
    def font_italic(self, value: bool) -> None:
        if bool(value) != self._font_italic:
            self._font_italic = bool(value)
            self.changed.emit()
