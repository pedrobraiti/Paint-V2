"""Catálogo de formas geométricas.

Cada forma é descrita como um ``QPainterPath`` normalizado dentro do retângulo
arrastado pelo usuário, o que faz todas responderem igual a Shift (proporção
travada) e Ctrl (desenhar do centro) sem precisar de código por forma.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath


@dataclass(frozen=True)
class ShapeDefinition:
    key: str
    label: str


SHAPES: tuple[ShapeDefinition, ...] = (
    ShapeDefinition("rectangle", "Retângulo"),
    ShapeDefinition("rounded_rectangle", "Retângulo arredondado"),
    ShapeDefinition("ellipse", "Elipse"),
    ShapeDefinition("triangle", "Triângulo"),
    ShapeDefinition("right_triangle", "Triângulo retângulo"),
    ShapeDefinition("diamond", "Losango"),
    ShapeDefinition("pentagon", "Pentágono"),
    ShapeDefinition("hexagon", "Hexágono"),
    ShapeDefinition("star_five", "Estrela de 5 pontas"),
    ShapeDefinition("star_six", "Estrela de 6 pontas"),
    ShapeDefinition("arrow_right", "Seta"),
    ShapeDefinition("heart", "Coração"),
    ShapeDefinition("lightning", "Raio"),
    ShapeDefinition("speech_bubble", "Balão de fala"),
)

SHAPES_BY_KEY = {shape.key: shape for shape in SHAPES}


def build_shape_path(kind: str, rect: QRectF) -> QPainterPath:
    """Caminho da forma inscrito em ``rect`` (já normalizado)."""
    rect = rect.normalized()
    builder = _BUILDERS.get(kind, _rectangle)
    return builder(rect)


def _relative(rect: QRectF, points: list[tuple[float, float]]) -> QPainterPath:
    """Converte coordenadas fracionárias (0..1) em um caminho fechado."""
    path = QPainterPath()
    for index, (fraction_x, fraction_y) in enumerate(points):
        point = QPointF(
            rect.left() + rect.width() * fraction_x,
            rect.top() + rect.height() * fraction_y,
        )
        if index == 0:
            path.moveTo(point)
        else:
            path.lineTo(point)
    path.closeSubpath()
    return path


def _polygon(rect: QRectF, sides: int, rotation: float = -math.pi / 2) -> QPainterPath:
    points = []
    for index in range(sides):
        angle = rotation + index * 2 * math.pi / sides
        points.append((0.5 + 0.5 * math.cos(angle), 0.5 + 0.5 * math.sin(angle)))
    return _relative(rect, points)


def _star(rect: QRectF, points_count: int, inner_ratio: float) -> QPainterPath:
    points = []
    for index in range(points_count * 2):
        radius = 0.5 if index % 2 == 0 else 0.5 * inner_ratio
        angle = -math.pi / 2 + index * math.pi / points_count
        points.append((0.5 + radius * math.cos(angle), 0.5 + radius * math.sin(angle)))
    return _relative(rect, points)


def _rectangle(rect: QRectF) -> QPainterPath:
    path = QPainterPath()
    path.addRect(rect)
    return path


def _rounded_rectangle(rect: QRectF) -> QPainterPath:
    radius = min(rect.width(), rect.height()) * 0.18
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def _ellipse(rect: QRectF) -> QPainterPath:
    path = QPainterPath()
    path.addEllipse(rect)
    return path


def _triangle(rect: QRectF) -> QPainterPath:
    return _relative(rect, [(0.5, 0.0), (1.0, 1.0), (0.0, 1.0)])


def _right_triangle(rect: QRectF) -> QPainterPath:
    return _relative(rect, [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0)])


def _diamond(rect: QRectF) -> QPainterPath:
    return _relative(rect, [(0.5, 0.0), (1.0, 0.5), (0.5, 1.0), (0.0, 0.5)])


def _arrow_right(rect: QRectF) -> QPainterPath:
    return _relative(
        rect,
        [
            (0.0, 0.32),
            (0.58, 0.32),
            (0.58, 0.05),
            (1.0, 0.5),
            (0.58, 0.95),
            (0.58, 0.68),
            (0.0, 0.68),
        ],
    )


def _heart(rect: QRectF) -> QPainterPath:
    width, height = rect.width(), rect.height()
    left, top = rect.left(), rect.top()

    def point(fraction_x: float, fraction_y: float) -> QPointF:
        return QPointF(left + width * fraction_x, top + height * fraction_y)

    path = QPainterPath(point(0.5, 1.0))
    path.cubicTo(point(-0.16, 0.52), point(0.12, -0.13), point(0.5, 0.27))
    path.cubicTo(point(0.88, -0.13), point(1.16, 0.52), point(0.5, 1.0))
    path.closeSubpath()
    return path


def _lightning(rect: QRectF) -> QPainterPath:
    return _relative(
        rect,
        [
            (0.52, 0.0),
            (0.16, 0.56),
            (0.44, 0.56),
            (0.30, 1.0),
            (0.84, 0.40),
            (0.54, 0.40),
            (0.78, 0.0),
        ],
    )


def _speech_bubble(rect: QRectF) -> QPainterPath:
    body = QRectF(
        rect.left(), rect.top(), rect.width(), max(rect.height() * 0.78, 1.0)
    )
    radius = min(body.width(), body.height()) * 0.22
    path = QPainterPath()
    path.addRoundedRect(body, radius, radius)
    tail = _relative(
        rect,
        [(0.22, 0.74), (0.40, 0.74), (0.24, 1.0)],
    )
    return path.united(tail)


_BUILDERS = {
    "rectangle": _rectangle,
    "rounded_rectangle": _rounded_rectangle,
    "ellipse": _ellipse,
    "triangle": _triangle,
    "right_triangle": _right_triangle,
    "diamond": _diamond,
    "pentagon": lambda rect: _polygon(rect, 5),
    "hexagon": lambda rect: _polygon(rect, 6),
    "star_five": lambda rect: _star(rect, 5, 0.42),
    "star_six": lambda rect: _star(rect, 6, 0.56),
    "arrow_right": _arrow_right,
    "heart": _heart,
    "lightning": _lightning,
    "speech_bubble": _speech_bubble,
}
