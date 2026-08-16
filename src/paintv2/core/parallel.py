"""Divisão do trabalho de um carimbo em faixas horizontais.

Um pincel de 2000 px cobre 4 milhões de pixels. Processado de uma vez, cada
etapa intermediária vira um array de dezenas de megabytes — o que trava a
interface e, em imagens grandes, chega a esgotar a memória. Fatiar o carimbo em
faixas resolve as duas coisas ao mesmo tempo:

* o pico de memória passa a depender do tamanho da faixa, não do pincel;
* as faixas são independentes, então rodam em paralelo — e as operações do NumPy
  liberam a GIL, de modo que threads de verdade usam todos os núcleos.

Modos que olham para os vizinhos (desfoque, nitidez) pedem uma **borda de
segurança**: a faixa é lida com algumas linhas a mais em cima e embaixo, e essas
linhas são descartadas na hora de escrever. Sem isso apareceria uma emenda
visível a cada divisão.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np

from .pixels import Rect

BAND_PIXEL_BUDGET = 32_000
HALO_BAND_RATIO = 6
MAX_WORKERS = min(16, (os.cpu_count() or 1))

_executor: ThreadPoolExecutor | None = None


@dataclass(frozen=True)
class Band:
    """Uma faixa horizontal de um carimbo."""

    rect: Rect
    """Área que será escrita."""

    padded: Rect
    """Área que precisa ser lida (``rect`` mais a borda de segurança)."""

    def crop(self, array: np.ndarray) -> np.ndarray:
        """Descarta as linhas da borda de segurança de um resultado."""
        offset = self.rect[1] - self.padded[1]
        return array[offset : offset + self.rect[3]]

    def rows_within(self, parent: Rect) -> slice:
        """Linhas ocupadas por esta faixa dentro do retângulo original."""
        start = self.rect[1] - parent[1]
        return slice(start, start + self.rect[3])


def split_into_bands(rect: Rect, halo: int = 0) -> Iterator[Band]:
    """Divide ``rect`` em faixas que cabem no orçamento de memória."""
    x, y, width, height = rect
    if width <= 0 or height <= 0:
        return

    rows_per_band = max(1, BAND_PIXEL_BUDGET // max(width, 1))
    if halo:
        # Cada faixa relê `halo` linhas em cima e embaixo. Se a faixa for fina, o
        # retrabalho passa do trabalho útil e dividir sai mais caro que não
        # dividir — daí o piso proporcional à borda.
        rows_per_band = max(rows_per_band, halo * HALO_BAND_RATIO)
    if height <= rows_per_band:
        yield Band(rect, rect)
        return

    # Distribuir as linhas igualmente em vez de encher cada faixa até o limite:
    # uma última faixa raquítica atrasa o conjunto (as threads esperam por ela)
    # e, com borda de segurança, é quase só retrabalho. O resto da divisão é
    # espalhado uma linha por faixa, então nenhuma difere da outra em mais de 1.
    band_count = -(-height // rows_per_band)
    base_height, remainder = divmod(height, band_count)

    top = y
    for index in range(band_count):
        band_height = base_height + (1 if index < remainder else 0)
        padded_top = max(y, top - halo)
        padded_bottom = min(y + height, top + band_height + halo)
        yield Band(
            rect=(x, top, width, band_height),
            padded=(x, padded_top, width, padded_bottom - padded_top),
        )
        top += band_height


def run_in_parallel(worker: Callable[[Band], None], bands: Iterable[Band]) -> None:
    """Executa ``worker`` para cada faixa e espera todas terminarem.

    Exceções levantadas nas threads são relançadas aqui — silenciá-las deixaria
    o traço com buracos sem nenhum aviso.
    """
    executor = _shared_executor()
    for future in [executor.submit(worker, band) for band in bands]:
        future.result()


def _shared_executor() -> ThreadPoolExecutor:
    """Pool criado uma vez e reaproveitado: abrir threads a cada carimbo custaria
    mais do que o trabalho que elas fazem."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(
            max_workers=MAX_WORKERS, thread_name_prefix="paintv2-band"
        )
    return _executor


def shutdown() -> None:
    """Encerra o pool — usado ao fechar o aplicativo e entre testes."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None
