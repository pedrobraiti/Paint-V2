"""Seleção ativa do documento.

A seleção é uma máscara booleana do tamanho do documento mais o retângulo que a
envolve. Guardar a máscara inteira (e não só o retângulo) é o que permite que o
laço à mão livre recorte de verdade, em vez de virar um retângulo disfarçado.
"""

from __future__ import annotations

import numpy as np

from .pixels import Rect, clip_rect


class Selection:
    """Região ativa; quando inativa, toda operação vale para o documento inteiro."""

    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._mask: np.ndarray | None = None
        self._bounds: Rect | None = None

    @property
    def is_active(self) -> bool:
        return self._mask is not None

    @property
    def bounds(self) -> Rect | None:
        return self._bounds

    @property
    def mask(self) -> np.ndarray | None:
        return self._mask

    def clear(self) -> None:
        self._mask = None
        self._bounds = None

    def resize_canvas(self, width: int, height: int) -> None:
        """Descarta a seleção quando o documento muda de tamanho."""
        self._width, self._height = width, height
        self.clear()

    def set_mask(self, mask: np.ndarray) -> None:
        """Define a seleção a partir de uma máscara booleana já do tamanho certo."""
        if not mask.any():
            self.clear()
            return
        self._mask = mask
        rows = np.flatnonzero(mask.any(axis=1))
        columns = np.flatnonzero(mask.any(axis=0))
        self._bounds = (
            int(columns[0]),
            int(rows[0]),
            int(columns[-1] - columns[0] + 1),
            int(rows[-1] - rows[0] + 1),
        )

    def set_rect(self, rect: Rect) -> None:
        """Seleção retangular, recortada aos limites do documento."""
        clipped = clip_rect(rect, self._width, self._height)
        if clipped is None:
            self.clear()
            return
        mask = np.zeros((self._height, self._width), dtype=bool)
        x, y, width, height = clipped
        mask[y : y + height, x : x + width] = True
        self._mask = mask
        self._bounds = clipped

    def select_all(self) -> None:
        self.set_rect((0, 0, self._width, self._height))

    def invert(self) -> None:
        if self._mask is None:
            self.select_all()
            return
        self.set_mask(~self._mask)

    def clip_weights(self) -> np.ndarray | None:
        """Máscara em ``float32``, no formato que o motor de traço consome."""
        if self._mask is None:
            return None
        return self._mask.astype(np.float32)

    def contains(self, x: int, y: int) -> bool:
        if self._mask is None:
            return False
        if not (0 <= x < self._width and 0 <= y < self._height):
            return False
        return bool(self._mask[y, x])
