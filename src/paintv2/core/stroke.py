"""Motor de traço: transforma um caminho do mouse em pixels alterados.

O ciclo é ``begin`` → vários ``move`` → ``end``. A cada passo o motor distribui
carimbos ao longo do caminho respeitando o espaçamento da ponta, acumula a máscara
do traço e pede ao modo que produza os pixels novos.

A máscara acumula em modo *screen* (``1 - (1-a)(1-b)``): pontas de fluxo total
saturam no primeiro toque — então repassar o pincel no mesmo lugar não intensifica
o efeito —, enquanto pontas translúcidas como Spray, Marcador e Aquarela vão
construindo cor camada a camada, que é o comportamento esperado delas.
"""

from __future__ import annotations

import math

import numpy as np

from .brush_modes import BrushMode
from .brush_tips import (
    MAX_SIZE,
    MIN_SIZE,
    StampRequest,
    TipDefinition,
    render_stamp,
    stamp_extent,
)
from .parallel import Band, run_in_parallel, split_into_bands
from .pixels import Rect, clip_rect, to_float, to_uint8, union_rect, view
from .snapshot import TileSnapshot


class StrokeBuffers:
    """Máscara de traço reutilizável, para não realocar a cada pincelada."""

    def __init__(self, height: int, width: int) -> None:
        self.mask = np.zeros((height, width), dtype=np.float32)

    def matches(self, height: int, width: int) -> bool:
        return self.mask.shape == (height, width)

    def clear(self, rect: Rect | None) -> None:
        if rect is None:
            self.mask[:] = 0.0
            return
        view(self.mask, rect)[:] = 0.0


class StrokeEngine:
    """Aplica um único traço contínuo sobre o buffer de pixels do documento."""

    def __init__(
        self,
        pixels: np.ndarray,
        tip: TipDefinition,
        mode: BrushMode,
        size: float,
        buffers: StrokeBuffers,
        seed: int | None = None,
        clip_mask: np.ndarray | None = None,
    ) -> None:
        self._pixels = pixels
        self._tip = tip
        self._mode = mode
        self._size = float(np.clip(size, MIN_SIZE, MAX_SIZE))
        self._buffers = buffers
        self._clip_mask = clip_mask
        self._rng = np.random.default_rng(seed)
        self._snapshot = TileSnapshot(pixels)
        self._last_point: tuple[float, float] | None = None
        self._last_pressure = 1.0
        self._distance_carry = 0.0
        self._dirty: Rect | None = None

    @property
    def dirty_rect(self) -> Rect | None:
        """Retângulo que engloba tudo que o traço alterou até agora."""
        return self._dirty

    @property
    def builds_up(self) -> bool:
        """Se a ponta continua depositando com o cursor parado (aerógrafo)."""
        return self._tip.builds_up

    def begin(self, x: float, y: float, pressure: float = 1.0) -> Rect | None:
        self._last_point = (x, y)
        self._last_pressure = pressure
        self._distance_carry = 0.0
        return self._stamp(x, y, pressure)

    def move(self, x: float, y: float, pressure: float = 1.0) -> Rect | None:
        if self._last_point is None:
            return self.begin(x, y, pressure)

        start_x, start_y = self._last_point
        delta_x, delta_y = x - start_x, y - start_y
        distance = math.hypot(delta_x, delta_y)
        step = max(self._tip.spacing * self._size, 1.0)

        dirty: Rect | None = None
        travelled = self._distance_carry
        while travelled + step <= distance:
            travelled += step
            ratio = travelled / distance
            pressure_at = self._last_pressure + (pressure - self._last_pressure) * ratio
            dirty = union_rect(
                dirty,
                self._stamp(start_x + delta_x * ratio, start_y + delta_y * ratio, pressure_at),
            )

        self._distance_carry = travelled - distance
        self._last_point = (x, y)
        self._last_pressure = pressure
        return dirty

    def dwell(self) -> Rect | None:
        """Carimbo extra na posição atual — só faz sentido para pontas que acumulam."""
        if not self._tip.builds_up or self._last_point is None:
            return None
        return self._stamp(*self._last_point, self._last_pressure)

    def end(self) -> Rect | None:
        self._buffers.clear(self._dirty)
        return self._dirty

    def original_region(self, rect: Rect) -> np.ndarray:
        """Pixels de antes do traço — o "antes" do patch de desfazer.

        Os ladrilhos foram preservados no caminho, então isso não custa uma nova
        varredura da imagem.
        """
        return self._snapshot.region(rect)

    def _stamp(self, x: float, y: float, pressure: float) -> Rect | None:
        size = self._effective_size(pressure)
        if self._tip.scatter:
            spread = self._tip.scatter * size
            x += float(self._rng.normal(0.0, spread))
            y += float(self._rng.normal(0.0, spread))

        request = StampRequest(size=size, rng=self._rng)
        extent = stamp_extent(self._tip, size)
        center_offset = (extent - 1) / 2.0
        left = math.floor(x - center_offset)
        top = math.floor(y - center_offset)
        request.offset_x = x - center_offset - left
        request.offset_y = y - center_offset - top

        alpha = render_stamp(self._tip, request)
        clipped = clip_rect((left, top, extent, extent), *self._canvas_size())
        if clipped is None:
            return None

        crop_x = clipped[0] - left
        crop_y = clipped[1] - top
        alpha = alpha[crop_y : crop_y + clipped[3], crop_x : crop_x + clipped[2]]
        if self._clip_mask is not None:
            alpha = alpha * view(self._clip_mask, clipped)
        if not alpha.any():
            return None

        flow = self._tip.flow * float(np.clip(pressure, 0.05, 1.0))
        if self._mode.sequential:
            self._apply_sequential(clipped, alpha * np.float32(flow))
        else:
            self._apply_accumulated(clipped, alpha * np.float32(flow))

        self._dirty = union_rect(self._dirty, clipped)
        return clipped

    def _apply_accumulated(self, rect: Rect, stamp: np.ndarray) -> None:
        mask_region = view(self._buffers.mask, rect)
        np.subtract(np.float32(1.0), mask_region, out=mask_region)
        mask_region *= np.float32(1.0) - stamp
        np.subtract(np.float32(1.0), mask_region, out=mask_region)

        # Capturar os ladrilhos antes de dividir o trabalho: é a única etapa que
        # escreve no dicionário do snapshot, e as bandas só leem.
        self._snapshot.preserve(rect)
        bands = list(split_into_bands(rect, self._mode.halo))
        if len(bands) == 1:
            self._process_band(bands[0])
            return
        run_in_parallel(self._process_band, bands)

    def _process_band(self, band: Band) -> None:
        base = to_float(self._snapshot.region(band.padded))
        mask = view(self._buffers.mask, band.padded)
        result = self._mode.apply(base, mask)
        view(self._pixels, band.rect)[:] = to_uint8(band.crop(result))

    def _apply_sequential(self, rect: Rect, stamp: np.ndarray) -> None:
        """Aplica um modo com estado, banda a banda e sempre na mesma ordem.

        Aqui não há paralelismo: o modo carrega estado entre as chamadas (o
        acumulador do blend), e duas threads mexendo nele embaralhariam o
        arrasto de cor.
        """
        self._snapshot.preserve(rect)
        for band in split_into_bands(rect, halo=0):
            target = view(self._pixels, band.rect)
            self._mode.set_band(band.rows_within(rect), (rect[3], rect[2]))
            current = to_float(target)
            stamp_band = stamp[band.rows_within(rect)]
            target[:] = to_uint8(self._mode.apply(current, stamp_band))

    def _effective_size(self, pressure: float) -> float:
        if pressure >= 0.999:
            return self._size
        # Quantizar evita recriar a máscara (e o acumulador do blend) a cada
        # micro-variação de pressão da caneta.
        scaled = self._size * (0.25 + 0.75 * float(np.clip(pressure, 0.0, 1.0)))
        return float(np.clip(round(scaled), MIN_SIZE, MAX_SIZE))

    def _canvas_size(self) -> tuple[int, int]:
        height, width = self._pixels.shape[:2]
        return width, height
