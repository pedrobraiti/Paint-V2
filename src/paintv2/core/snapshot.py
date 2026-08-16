"""Cópia preguiçosa do estado de um buffer, feita por ladrilhos.

Pincéis de efeito precisam ler os pixels *originais* do início do traço — senão o
efeito se acumula sobre si mesmo e passar o mouse devagar produz um resultado
diferente de passar rápido. Copiar a imagem inteira a cada traço custa caro numa
foto grande, então aqui só os ladrilhos realmente tocados são preservados, e
sempre antes da primeira escrita neles.
"""

from __future__ import annotations

import numpy as np

from .pixels import Rect

TILE_SIZE = 256


class TileSnapshot:
    """Guarda o estado original de ``source`` sob demanda, ladrilho a ladrilho."""

    def __init__(self, source: np.ndarray, tile_size: int = TILE_SIZE) -> None:
        self._source = source
        self._tile_size = tile_size
        self._tiles: dict[tuple[int, int], np.ndarray] = {}

    @property
    def tile_count(self) -> int:
        """Quantos ladrilhos já foram preservados — usado em testes e diagnóstico."""
        return len(self._tiles)

    def preserve(self, rect: Rect) -> None:
        """Captura os ladrilhos que cobrem ``rect``, se ainda não capturados.

        Precisa rodar **antes** de qualquer escrita no retângulo — e, quando o
        trabalho é dividido entre threads, antes de elas começarem: é a única
        parte que altera o dicionário de ladrilhos.
        """
        self._preserve(rect)

    def region(self, rect: Rect) -> np.ndarray:
        """Pixels originais dentro de ``rect``, como cópia contígua.

        Só lê ladrilhos já capturados, então é seguro chamar de várias threads
        depois de um :meth:`preserve` que cubra a área toda.
        """
        x, y, width, height = rect
        self._preserve(rect)
        out = np.empty((height, width, self._source.shape[2]), dtype=self._source.dtype)
        for tile_y, tile_x, tile in self._tiles_covering(rect):
            src_x0 = max(x, tile_x) - tile_x
            src_y0 = max(y, tile_y) - tile_y
            src_x1 = min(x + width, tile_x + tile.shape[1]) - tile_x
            src_y1 = min(y + height, tile_y + tile.shape[0]) - tile_y
            dst_x0 = tile_x + src_x0 - x
            dst_y0 = tile_y + src_y0 - y
            out[
                dst_y0 : dst_y0 + (src_y1 - src_y0),
                dst_x0 : dst_x0 + (src_x1 - src_x0),
            ] = tile[src_y0:src_y1, src_x0:src_x1]
        return out

    def _preserve(self, rect: Rect) -> None:
        x, y, width, height = rect
        height_limit, width_limit = self._source.shape[:2]
        for tile_y in range(
            (y // self._tile_size) * self._tile_size, y + height, self._tile_size
        ):
            for tile_x in range(
                (x // self._tile_size) * self._tile_size, x + width, self._tile_size
            ):
                key = (tile_y, tile_x)
                if key in self._tiles:
                    continue
                bottom = min(tile_y + self._tile_size, height_limit)
                right = min(tile_x + self._tile_size, width_limit)
                self._tiles[key] = self._source[tile_y:bottom, tile_x:right].copy()

    def _tiles_covering(self, rect: Rect):
        x, y, width, height = rect
        for tile_y in range(
            (y // self._tile_size) * self._tile_size, y + height, self._tile_size
        ):
            for tile_x in range(
                (x // self._tile_size) * self._tile_size, x + width, self._tile_size
            ):
                tile = self._tiles.get((tile_y, tile_x))
                if tile is not None and tile.size:
                    yield tile_y, tile_x, tile
