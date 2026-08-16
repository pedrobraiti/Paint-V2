"""Ícones vetoriais desenhados em tempo de execução.

Nenhum arquivo de imagem é embarcado: cada ícone é um traçado sobre uma grade de
24×24 pixels, redesenhado no tamanho e na cor pedidos. Isso mantém o conjunto
coerente, nítido em qualquer DPI e permite recolorir o ícone conforme o estado do
botão sem gerar variantes em disco.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from .theme import PALETTE

GRID = 24.0
STROKE_WIDTH = 1.9

Drawer = Callable[[QPainter], None]


def _path(*points: tuple[float, float]) -> QPainterPath:
    path = QPainterPath(QPointF(*points[0]))
    for point in points[1:]:
        path.lineTo(QPointF(*point))
    return path


def _circle(painter: QPainter, x: float, y: float, radius: float) -> None:
    painter.drawEllipse(QPointF(x, y), radius, radius)


def _dot(painter: QPainter, x: float, y: float, radius: float = 1.6) -> None:
    painter.save()
    painter.setBrush(painter.pen().color())
    painter.setPen(Qt.PenStyle.NoPen)
    _circle(painter, x, y, radius)
    painter.restore()


def _with_width(painter: QPainter, width: float) -> QPen:
    pen = QPen(painter.pen())
    pen.setWidthF(width)
    painter.setPen(pen)
    return pen


def _dashed(painter: QPainter) -> None:
    pen = QPen(painter.pen())
    pen.setStyle(Qt.PenStyle.DashLine)
    pen.setDashPattern([2.4, 2.0])
    painter.setPen(pen)


# --------------------------------------------------------------------- arquivo


def _home(painter: QPainter) -> None:
    painter.drawPath(_path((3.5, 11.0), (12.0, 3.5), (20.5, 11.0)))
    painter.drawPath(_path((6.0, 10.0), (6.0, 20.0), (18.0, 20.0), (18.0, 10.0)))
    painter.drawPath(_path((10.0, 20.0), (10.0, 14.5), (14.0, 14.5), (14.0, 20.0)))


def _folder(painter: QPainter) -> None:
    painter.drawPath(
        _path((3.0, 19.5), (3.0, 5.5), (9.0, 5.5), (11.2, 8.5), (20.0, 8.5), (20.0, 11.5))
    )
    painter.drawPath(_path((3.0, 19.5), (6.2, 11.5), (22.0, 11.5), (18.8, 19.5), (3.0, 19.5)))


def _save(painter: QPainter) -> None:
    painter.drawPath(
        _path((4.0, 4.0), (16.0, 4.0), (20.0, 8.0), (20.0, 20.0), (4.0, 20.0), (4.0, 4.0))
    )
    painter.drawPath(_path((8.0, 4.0), (8.0, 10.0), (15.0, 10.0), (15.0, 4.0)))
    painter.drawRect(QRectF(7.5, 13.5, 9.0, 6.5))


def _new_file(painter: QPainter) -> None:
    painter.drawPath(
        _path((13.0, 3.0), (6.0, 3.0), (6.0, 21.0), (18.0, 21.0), (18.0, 8.0), (13.0, 3.0))
    )
    painter.drawPath(_path((13.0, 3.0), (13.0, 8.0), (18.0, 8.0)))


def _image(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(3.0, 5.0, 18.0, 14.0), 2.5, 2.5)
    _dot(painter, 8.2, 10.0, 1.5)
    painter.drawPath(_path((4.5, 17.5), (10.0, 12.0), (13.0, 15.0), (16.0, 12.5), (20.0, 17.0)))


def _trash(painter: QPainter) -> None:
    painter.drawLine(QPointF(3.5, 6.5), QPointF(20.5, 6.5))
    painter.drawPath(_path((9.0, 6.5), (9.0, 3.5), (15.0, 3.5), (15.0, 6.5)))
    painter.drawPath(_path((5.8, 6.5), (7.0, 20.5), (17.0, 20.5), (18.2, 6.5)))
    painter.drawLine(QPointF(10.0, 10.0), QPointF(10.0, 17.0))
    painter.drawLine(QPointF(14.0, 10.0), QPointF(14.0, 17.0))


# --------------------------------------------------------------------- edição


def _undo(painter: QPainter) -> None:
    painter.drawPath(_path((9.0, 6.0), (4.0, 11.0), (9.0, 16.0)))
    path = QPainterPath(QPointF(4.0, 11.0))
    path.lineTo(13.5, 11.0)
    path.cubicTo(QPointF(19.5, 11.0), QPointF(20.5, 15.0), QPointF(18.5, 19.5))
    painter.drawPath(path)


def _redo(painter: QPainter) -> None:
    painter.drawPath(_path((15.0, 6.0), (20.0, 11.0), (15.0, 16.0)))
    path = QPainterPath(QPointF(20.0, 11.0))
    path.lineTo(10.5, 11.0)
    path.cubicTo(QPointF(4.5, 11.0), QPointF(3.5, 15.0), QPointF(5.5, 19.5))
    painter.drawPath(path)


def _cut(painter: QPainter) -> None:
    painter.drawLine(QPointF(6.5, 4.0), QPointF(16.5, 16.5))
    painter.drawLine(QPointF(17.5, 4.0), QPointF(7.5, 16.5))
    _circle(painter, 6.0, 19.0, 2.4)
    _circle(painter, 18.0, 19.0, 2.4)


def _copy(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(3.5, 3.5, 12.0, 12.0), 2.0, 2.0)
    painter.drawRoundedRect(QRectF(8.5, 8.5, 12.0, 12.0), 2.0, 2.0)


def _paste(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(4.5, 4.5, 15.0, 16.0), 2.5, 2.5)
    painter.drawRoundedRect(QRectF(8.5, 2.5, 7.0, 4.0), 1.5, 1.5)
    painter.drawLine(QPointF(8.0, 11.0), QPointF(16.0, 11.0))
    painter.drawLine(QPointF(8.0, 15.0), QPointF(14.0, 15.0))


def _crop(painter: QPainter) -> None:
    painter.drawPath(_path((6.5, 2.0), (6.5, 17.5), (22.0, 17.5)))
    painter.drawPath(_path((2.0, 6.5), (17.5, 6.5), (17.5, 22.0)))


def _select_rect(painter: QPainter) -> None:
    _dashed(painter)
    painter.drawRect(QRectF(3.5, 3.5, 17.0, 17.0))


def _select_lasso(painter: QPainter) -> None:
    path = QPainterPath(QPointF(5.0, 11.0))
    path.cubicTo(QPointF(4.0, 3.5), QPointF(20.0, 3.5), QPointF(19.0, 11.0))
    path.cubicTo(QPointF(18.0, 17.0), QPointF(7.0, 14.5), QPointF(8.0, 19.0))
    painter.drawPath(path)
    _dot(painter, 8.4, 20.5, 1.6)


# -------------------------------------------------------------------- pincéis


def _pencil(painter: QPainter) -> None:
    painter.drawPath(
        _path((3.5, 20.5), (4.5, 16.0), (15.5, 5.0), (19.0, 8.5), (8.0, 19.5), (3.5, 20.5))
    )
    painter.drawLine(QPointF(13.0, 7.5), QPointF(16.5, 11.0))


def _brush(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(10.2, 2.5, 3.6, 8.0), 1.6, 1.6)
    painter.drawRect(QRectF(9.0, 11.0, 6.0, 2.6))
    painter.drawPath(_path((9.0, 14.2), (15.0, 14.2), (13.6, 21.0), (10.4, 21.0), (9.0, 14.2)))


def _spray(painter: QPainter) -> None:
    painter.drawRoundedRect(QRectF(6.0, 8.5, 8.5, 12.5), 2.0, 2.0)
    painter.drawRect(QRectF(8.6, 5.0, 3.3, 3.5))
    for x, y in ((17.5, 5.5), (20.5, 8.0), (17.0, 10.5), (20.0, 13.0), (17.5, 15.5)):
        _dot(painter, x, y, 1.15)


def _eraser(painter: QPainter) -> None:
    painter.drawPath(_path((3.0, 15.0), (11.0, 7.0), (18.0, 14.0), (10.0, 22.0), (3.0, 15.0)))
    painter.drawLine(QPointF(7.5, 10.5), QPointF(14.5, 17.5))
    painter.drawLine(QPointF(10.0, 22.0), QPointF(21.0, 22.0))


def _fill(painter: QPainter) -> None:
    painter.drawPath(_path((5.0, 12.0), (12.0, 5.0), (20.0, 13.0), (13.0, 20.0), (5.0, 12.0)))
    painter.drawLine(QPointF(8.5, 8.5), QPointF(8.5, 4.0))
    drop = QPainterPath(QPointF(21.0, 14.0))
    drop.cubicTo(QPointF(23.5, 17.5), QPointF(23.0, 20.5), QPointF(21.0, 20.5))
    drop.cubicTo(QPointF(19.0, 20.5), QPointF(18.5, 17.5), QPointF(21.0, 14.0))
    painter.drawPath(drop)


def _picker(painter: QPainter) -> None:
    painter.drawPath(_path((2.8, 21.2), (3.8, 17.4), (13.0, 8.2), (15.8, 11.0), (6.6, 20.2), (2.8, 21.2)))
    painter.save()
    _with_width(painter, 3.4)
    painter.drawLine(QPointF(15.4, 6.6), QPointF(19.4, 2.6))
    painter.restore()
    painter.drawLine(QPointF(13.0, 8.2), QPointF(15.8, 11.0))


def _text(painter: QPainter) -> None:
    painter.drawPath(_path((4.5, 20.0), (12.0, 4.0), (19.5, 20.0)))
    painter.drawLine(QPointF(8.0, 14.5), QPointF(16.0, 14.5))


def _line(painter: QPainter) -> None:
    painter.drawLine(QPointF(5.0, 19.0), QPointF(19.0, 5.0))
    _dot(painter, 5.0, 19.0)
    _dot(painter, 19.0, 5.0)


def _curve(painter: QPainter) -> None:
    path = QPainterPath(QPointF(4.0, 18.5))
    path.cubicTo(QPointF(8.0, 5.0), QPointF(16.0, 21.0), QPointF(20.0, 6.5))
    painter.drawPath(path)
    _dot(painter, 4.0, 18.5)
    _dot(painter, 20.0, 6.5)


def _shapes(painter: QPainter) -> None:
    painter.drawRect(QRectF(3.0, 6.0, 11.0, 11.0))
    _circle(painter, 16.0, 15.0, 5.5)


def _zoom_in(painter: QPainter) -> None:
    _circle(painter, 10.5, 10.5, 6.6)
    painter.drawLine(QPointF(15.4, 15.4), QPointF(21.0, 21.0))
    painter.drawLine(QPointF(7.6, 10.5), QPointF(13.4, 10.5))
    painter.drawLine(QPointF(10.5, 7.6), QPointF(10.5, 13.4))


def _zoom_out(painter: QPainter) -> None:
    _circle(painter, 10.5, 10.5, 6.6)
    painter.drawLine(QPointF(15.4, 15.4), QPointF(21.0, 21.0))
    painter.drawLine(QPointF(7.6, 10.5), QPointF(13.4, 10.5))


def _hand(painter: QPainter) -> None:
    painter.drawPath(
        _path((6.5, 13.0), (6.5, 10.0), (9.5, 10.0), (9.5, 4.5))
    )
    painter.drawLine(QPointF(12.5, 10.0), QPointF(12.5, 3.5))
    painter.drawLine(QPointF(15.5, 10.5), QPointF(15.5, 5.5))
    path = QPainterPath(QPointF(6.5, 12.0))
    path.lineTo(QPointF(6.5, 16.0))
    path.cubicTo(QPointF(6.5, 20.5), QPointF(10.0, 21.5), QPointF(13.5, 21.5))
    path.cubicTo(QPointF(17.0, 21.5), QPointF(18.5, 19.0), QPointF(18.5, 15.0))
    path.lineTo(QPointF(18.5, 8.5))
    painter.drawPath(path)


# --------------------------------------------------------------------- efeitos


def _droplet_path() -> QPainterPath:
    path = QPainterPath(QPointF(12.0, 2.6))
    path.lineTo(QPointF(17.6, 10.4))
    path.cubicTo(QPointF(20.6, 15.0), QPointF(17.2, 20.8), QPointF(12.0, 20.8))
    path.cubicTo(QPointF(6.8, 20.8), QPointF(3.4, 15.0), QPointF(6.4, 10.4))
    path.closeSubpath()
    return path


def _saturation(painter: QPainter) -> None:
    droplet = _droplet_path()
    painter.save()
    fill = QColor(painter.pen().color())
    fill.setAlphaF(0.32)
    painter.setBrush(fill)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setClipRect(QRectF(0.0, 12.0, GRID, GRID))
    painter.drawPath(droplet)
    painter.restore()
    painter.drawPath(droplet)


def _blend(painter: QPainter) -> None:
    first = QPainterPath(QPointF(3.5, 15.5))
    first.cubicTo(QPointF(8.0, 6.5), QPointF(14.0, 17.0), QPointF(20.5, 8.0))
    painter.drawPath(first)
    second = QPainterPath(QPointF(3.5, 20.5))
    second.cubicTo(QPointF(8.0, 11.5), QPointF(14.0, 22.0), QPointF(20.5, 13.0))
    painter.drawPath(second)
    _dot(painter, 19.5, 5.0, 2.2)


def _blur(painter: QPainter) -> None:
    painter.save()
    _dashed(painter)
    _circle(painter, 12.0, 12.0, 8.4)
    painter.restore()
    _circle(painter, 12.0, 12.0, 5.0)
    _dot(painter, 12.0, 12.0, 2.0)


def _sharpen(painter: QPainter) -> None:
    painter.drawPath(_path((12.0, 3.5), (19.5, 19.5), (4.5, 19.5), (12.0, 3.5)))
    painter.drawLine(QPointF(12.0, 10.0), QPointF(12.0, 16.0))


def _dodge(painter: QPainter) -> None:
    _circle(painter, 12.0, 12.0, 4.6)
    for x1, y1, x2, y2 in (
        (12.0, 2.5, 12.0, 5.2),
        (12.0, 18.8, 12.0, 21.5),
        (2.5, 12.0, 5.2, 12.0),
        (18.8, 12.0, 21.5, 12.0),
        (5.4, 5.4, 7.3, 7.3),
        (16.7, 16.7, 18.6, 18.6),
        (18.6, 5.4, 16.7, 7.3),
        (7.3, 16.7, 5.4, 18.6),
    ):
        painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def _burn(painter: QPainter) -> None:
    flame = QPainterPath(QPointF(12.0, 2.2))
    flame.cubicTo(QPointF(17.0, 7.5), QPointF(18.4, 10.5), QPointF(18.4, 14.0))
    flame.cubicTo(QPointF(18.4, 18.0), QPointF(15.5, 21.4), QPointF(12.0, 21.4))
    flame.cubicTo(QPointF(8.5, 21.4), QPointF(5.6, 18.0), QPointF(5.6, 14.0))
    flame.cubicTo(QPointF(5.6, 10.0), QPointF(9.0, 8.0), QPointF(9.8, 4.4))
    flame.cubicTo(QPointF(10.6, 8.0), QPointF(11.2, 6.0), QPointF(12.0, 2.2))
    painter.drawPath(flame)
    inner = QPainterPath(QPointF(12.0, 12.4))
    inner.cubicTo(QPointF(14.2, 14.6), QPointF(14.6, 16.4), QPointF(14.0, 18.0))
    inner.cubicTo(QPointF(13.4, 19.8), QPointF(10.6, 19.8), QPointF(10.0, 18.0))
    inner.cubicTo(QPointF(9.4, 16.2), QPointF(10.6, 14.4), QPointF(12.0, 12.4))
    painter.drawPath(inner)


def _contrast(painter: QPainter) -> None:
    """Círculo com metade cheia — o símbolo clássico de contraste."""
    painter.save()
    painter.setBrush(painter.pen().color())
    painter.setPen(Qt.PenStyle.NoPen)
    half = QPainterPath(QPointF(12.0, 3.4))
    half.arcTo(QRectF(3.4, 3.4, 17.2, 17.2), 90.0, -180.0)
    half.closeSubpath()
    painter.drawPath(half)
    painter.restore()
    _circle(painter, 12.0, 12.0, 8.6)


def _levels(painter: QPainter) -> None:
    """Curva em S dentro de uma moldura, como num editor de curvas."""
    painter.drawRect(QRectF(3.5, 3.5, 17.0, 17.0))
    curve = QPainterPath(QPointF(3.5, 20.5))
    curve.cubicTo(QPointF(11.0, 19.0), QPointF(13.0, 5.0), QPointF(20.5, 3.5))
    painter.drawPath(curve)


def _hue(painter: QPainter) -> None:
    _circle(painter, 12.0, 12.0, 8.4)
    _dot(painter, 12.0, 7.4, 2.0)
    _dot(painter, 8.0, 14.3, 2.0)
    _dot(painter, 16.0, 14.3, 2.0)


def _adjustments(painter: QPainter) -> None:
    for y, knob in ((6.5, 9.0), (12.0, 15.0), (17.5, 7.5)):
        painter.drawLine(QPointF(3.5, y), QPointF(20.5, y))
        _dot(painter, knob, y, 2.2)


# ------------------------------------------------------------------- imagem


def _rotate_right(painter: QPainter) -> None:
    path = QPainterPath()
    path.arcMoveTo(QRectF(4.0, 4.0, 16.0, 16.0), 90.0)
    path.arcTo(QRectF(4.0, 4.0, 16.0, 16.0), 90.0, -280.0)
    painter.drawPath(path)
    painter.drawPath(_path((8.5, 1.5), (12.0, 4.0), (8.5, 6.5)))


def _rotate_left(painter: QPainter) -> None:
    path = QPainterPath()
    path.arcMoveTo(QRectF(4.0, 4.0, 16.0, 16.0), 90.0)
    path.arcTo(QRectF(4.0, 4.0, 16.0, 16.0), 90.0, 280.0)
    painter.drawPath(path)
    painter.drawPath(_path((15.5, 1.5), (12.0, 4.0), (15.5, 6.5)))


def _flip_horizontal(painter: QPainter) -> None:
    painter.save()
    _dashed(painter)
    painter.drawLine(QPointF(12.0, 2.5), QPointF(12.0, 21.5))
    painter.restore()
    painter.drawPath(_path((9.5, 7.0), (3.0, 12.0), (9.5, 17.0), (9.5, 7.0)))
    painter.drawPath(_path((14.5, 7.0), (21.0, 12.0), (14.5, 17.0), (14.5, 7.0)))


def _flip_vertical(painter: QPainter) -> None:
    painter.save()
    _dashed(painter)
    painter.drawLine(QPointF(2.5, 12.0), QPointF(21.5, 12.0))
    painter.restore()
    painter.drawPath(_path((7.0, 9.5), (12.0, 3.0), (17.0, 9.5), (7.0, 9.5)))
    painter.drawPath(_path((7.0, 14.5), (12.0, 21.0), (17.0, 14.5), (7.0, 14.5)))


def _resize(painter: QPainter) -> None:
    painter.drawRect(QRectF(3.5, 3.5, 17.0, 17.0))
    painter.drawLine(QPointF(8.0, 16.0), QPointF(16.0, 8.0))
    painter.drawPath(_path((8.0, 12.0), (8.0, 16.0), (12.0, 16.0)))
    painter.drawPath(_path((12.0, 8.0), (16.0, 8.0), (16.0, 12.0)))


def _grid(painter: QPainter) -> None:
    painter.drawRect(QRectF(3.5, 3.5, 17.0, 17.0))
    painter.drawLine(QPointF(9.2, 3.5), QPointF(9.2, 20.5))
    painter.drawLine(QPointF(14.8, 3.5), QPointF(14.8, 20.5))
    painter.drawLine(QPointF(3.5, 9.2), QPointF(20.5, 9.2))
    painter.drawLine(QPointF(3.5, 14.8), QPointF(20.5, 14.8))


def _palette(painter: QPainter) -> None:
    path = QPainterPath()
    path.addEllipse(QRectF(2.5, 3.5, 19.0, 17.0))
    painter.drawPath(path)
    _circle(painter, 16.5, 15.0, 2.4)
    _dot(painter, 8.0, 8.5, 1.6)
    _dot(painter, 13.5, 7.0, 1.6)
    _dot(painter, 6.5, 14.0, 1.6)


def _plus(painter: QPainter) -> None:
    painter.drawLine(QPointF(12.0, 5.0), QPointF(12.0, 19.0))
    painter.drawLine(QPointF(5.0, 12.0), QPointF(19.0, 12.0))


def _chevron_left(painter: QPainter) -> None:
    painter.drawPath(_path((15.0, 4.5), (8.0, 12.0), (15.0, 19.5)))


def _info(painter: QPainter) -> None:
    _circle(painter, 12.0, 12.0, 8.6)
    painter.drawLine(QPointF(12.0, 11.0), QPointF(12.0, 16.5))
    _dot(painter, 12.0, 7.6, 1.2)


DRAWERS: dict[str, Drawer] = {
    "home": _home,
    "folder": _folder,
    "save": _save,
    "new_file": _new_file,
    "image": _image,
    "trash": _trash,
    "undo": _undo,
    "redo": _redo,
    "cut": _cut,
    "copy": _copy,
    "paste": _paste,
    "crop": _crop,
    "select_rect": _select_rect,
    "select_lasso": _select_lasso,
    "pencil": _pencil,
    "brush": _brush,
    "spray": _spray,
    "eraser": _eraser,
    "fill": _fill,
    "picker": _picker,
    "text": _text,
    "line": _line,
    "curve": _curve,
    "shapes": _shapes,
    "zoom_in": _zoom_in,
    "zoom_out": _zoom_out,
    "hand": _hand,
    "saturation": _saturation,
    "blend": _blend,
    "blur": _blur,
    "sharpen": _sharpen,
    "dodge": _dodge,
    "burn": _burn,
    "hue": _hue,
    "contrast": _contrast,
    "levels": _levels,
    "adjustments": _adjustments,
    "rotate_right": _rotate_right,
    "rotate_left": _rotate_left,
    "flip_horizontal": _flip_horizontal,
    "flip_vertical": _flip_vertical,
    "resize": _resize,
    "grid": _grid,
    "palette": _palette,
    "plus": _plus,
    "chevron_left": _chevron_left,
    "info": _info,
}


@lru_cache(maxsize=256)
def icon_pixmap(kind: str, size: int, color: str) -> QPixmap:
    """Rasteriza um ícone no tamanho e cor pedidos."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    drawer = DRAWERS.get(kind)
    if drawer is None:
        return pixmap

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(size / GRID, size / GRID)

    pen = QPen(QColor(color))
    pen.setWidthF(STROKE_WIDTH)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    drawer(painter)
    painter.end()
    return pixmap


@lru_cache(maxsize=256)
def get_icon(kind: str, size: int = 22, color: str | None = None) -> QIcon:
    """``QIcon`` com variantes normal e desabilitada já embutidas."""
    icon = QIcon()
    icon.addPixmap(icon_pixmap(kind, size, color or PALETTE.text), QIcon.Mode.Normal)
    icon.addPixmap(icon_pixmap(kind, size, PALETTE.text_disabled), QIcon.Mode.Disabled)
    icon.addPixmap(icon_pixmap(kind, size, color or PALETTE.accent), QIcon.Mode.Active)
    return icon


def available_icons() -> tuple[str, ...]:
    """Nomes de todos os ícones — usado nos testes para garantir cobertura."""
    return tuple(DRAWERS)
