"""Preenchimento por região (balde de tinta) e seleção por cor.

Diferente do Paint clássico, a comparação aceita tolerância: pixels *parecidos*
com o clicado entram na região, o que resolve o caso comum de preencher uma área
de uma foto com ruído ou compressão JPEG.
"""

from __future__ import annotations

import numpy as np

from .pixels import Rect

MAX_TOLERANCE = 100.0


def similarity_mask(
    pixels: np.ndarray, origin_x: int, origin_y: int, tolerance: float
) -> np.ndarray:
    """Máscara booleana dos pixels cuja cor se aproxima da do ponto de origem."""
    reference = pixels[origin_y, origin_x].astype(np.int16)
    difference = pixels.astype(np.int16) - reference
    distance = np.sqrt(np.sum(difference.astype(np.float32) ** 2, axis=2))
    # A diagonal do cubo RGBA (255 * 2) é a distância máxima possível.
    threshold = (np.clip(tolerance, 0.0, MAX_TOLERANCE) / MAX_TOLERANCE) * 510.0
    return distance <= threshold


def contiguous_region(
    similar: np.ndarray, origin_x: int, origin_y: int
) -> tuple[np.ndarray, Rect]:
    """Componente conexa de ``similar`` que contém a origem, por varredura de linhas.

    Percorre spans horizontais inteiros em vez de pixel a pixel: o custo passa a
    ser proporcional ao número de segmentos da região, não à sua área.
    """
    height, width = similar.shape
    filled = np.zeros_like(similar, dtype=bool)
    if not similar[origin_y, origin_x]:
        return filled, (origin_x, origin_y, 0, 0)

    min_x, max_x = origin_x, origin_x
    min_y, max_y = origin_y, origin_y
    stack: list[tuple[int, int, int]] = [(origin_y, origin_x, origin_x)]

    while stack:
        row, seed_left, seed_right = stack.pop()
        line = similar[row]
        done = filled[row]

        left = seed_left
        while left > 0 and line[left - 1] and not done[left - 1]:
            left -= 1
        right = seed_right
        while right < width - 1 and line[right + 1] and not done[right + 1]:
            right += 1

        if done[left:right + 1].all():
            continue
        done[left : right + 1] = True

        min_x, max_x = min(min_x, left), max(max_x, right)
        min_y, max_y = min(min_y, row), max(max_y, row)

        for neighbour in (row - 1, row + 1):
            if not 0 <= neighbour < height:
                continue
            neighbour_line = similar[neighbour]
            neighbour_done = filled[neighbour]
            column = left
            while column <= right:
                if neighbour_line[column] and not neighbour_done[column]:
                    span_start = column
                    while column <= right and neighbour_line[column]:
                        column += 1
                    stack.append((neighbour, span_start, column - 1))
                else:
                    column += 1

    return filled, (min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)


def flood_fill(
    pixels: np.ndarray,
    origin_x: int,
    origin_y: int,
    color: np.ndarray,
    tolerance: float = 0.0,
    contiguous: bool = True,
) -> Rect | None:
    """Pinta a região a partir de ``(origin_x, origin_y)``.

    Devolve o retângulo alterado, ou ``None`` se o clique caiu fora da imagem ou
    nada mudou.
    """
    height, width = pixels.shape[:2]
    if not (0 <= origin_x < width and 0 <= origin_y < height):
        return None

    similar = similarity_mask(pixels, origin_x, origin_y, tolerance)
    if contiguous:
        region, rect = contiguous_region(similar, origin_x, origin_y)
    else:
        region = similar
        rows = np.flatnonzero(region.any(axis=1))
        columns = np.flatnonzero(region.any(axis=0))
        if not rows.size or not columns.size:
            return None
        rect = (
            int(columns[0]),
            int(rows[0]),
            int(columns[-1] - columns[0] + 1),
            int(rows[-1] - rows[0] + 1),
        )

    if not region.any():
        return None

    pixels[region] = np.asarray(color, dtype=np.uint8)
    return rect
