"""Pontas de pincel: a *forma* do carimbo, independente do que ele faz.

Uma ponta só sabe produzir uma máscara alpha ``float32`` em ``[0, 1]``. Quem
decide o que acontece com os pixels sob essa máscara é o modo
(:mod:`paintv2.core.brush_modes`). Essa separação é o que permite usar o Spray ou
a Caligrafia tanto para pintar quanto para saturar, borrar ou desfocar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

MIN_SIZE = 1.0
MAX_SIZE = 500.0
SUBPIXEL_STEPS = 4


@dataclass(frozen=True)
class TipDefinition:
    """Parâmetros que descrevem uma ponta de pincel."""

    key: str
    label: str
    description: str
    shape: str = "round"
    hardness: float = 0.85
    spacing: float = 0.12
    flow: float = 1.0
    angle: float = 0.0
    aspect: float = 1.0
    grain: float = 0.0
    grain_scale: float = 1.0
    scatter: float = 0.0
    density: float = 0.6
    builds_up: bool = False
    aliased: bool = False

    @property
    def is_stochastic(self) -> bool:
        """Se cada carimbo é único, o cache de máscaras não pode ser usado."""
        return self.shape == "spray" or self.grain > 0.0


TIPS: tuple[TipDefinition, ...] = (
    TipDefinition(
        key="pencil",
        label="Lápis",
        description="Traço duro de um pixel, sem suavização — igual ao lápis do Paint.",
        shape="square",
        hardness=1.0,
        spacing=0.05,
        aliased=True,
    ),
    TipDefinition(
        key="brush",
        label="Pincel",
        description="Ponta redonda com borda levemente suave. O padrão para tudo.",
        hardness=0.75,
        spacing=0.10,
    ),
    TipDefinition(
        key="soft",
        label="Pincel macio",
        description="Queda bem gradual até a borda; ideal para efeitos sutis.",
        hardness=0.0,
        spacing=0.08,
        flow=0.85,
    ),
    TipDefinition(
        key="square",
        label="Pincel quadrado",
        description="Carimbo quadrado de borda dura.",
        shape="square",
        hardness=0.95,
        spacing=0.10,
    ),
    TipDefinition(
        key="calligraphy_1",
        label="Caligrafia 1",
        description="Ponta chata inclinada a 45°, que afina conforme a direção do traço.",
        shape="ellipse",
        hardness=0.9,
        spacing=0.06,
        angle=45.0,
        aspect=0.22,
    ),
    TipDefinition(
        key="calligraphy_2",
        label="Caligrafia 2",
        description="Ponta chata inclinada a 135°, espelho da Caligrafia 1.",
        shape="ellipse",
        hardness=0.9,
        spacing=0.06,
        angle=135.0,
        aspect=0.22,
    ),
    TipDefinition(
        key="airbrush",
        label="Spray",
        description="Aerógrafo: partículas dispersas que continuam a se acumular parado.",
        shape="spray",
        hardness=0.0,
        spacing=0.05,
        flow=0.35,
        density=0.5,
        builds_up=True,
    ),
    TipDefinition(
        key="marker",
        label="Marcador",
        description="Ponta chata translúcida que escurece onde o traço se cruza.",
        shape="ellipse",
        hardness=1.0,
        spacing=0.05,
        flow=0.45,
        angle=30.0,
        aspect=0.55,
    ),
    TipDefinition(
        key="oil",
        label="Pincel de óleo",
        description="Cerdas visíveis, cobertura densa e borda irregular.",
        hardness=0.6,
        spacing=0.05,
        flow=0.8,
        grain=0.45,
        grain_scale=3.0,
    ),
    TipDefinition(
        key="crayon",
        label="Giz de cera",
        description="Textura granulada que deixa o papel aparecer por baixo.",
        hardness=0.9,
        spacing=0.07,
        flow=0.7,
        grain=0.8,
        grain_scale=1.6,
    ),
    TipDefinition(
        key="natural_pencil",
        label="Lápis natural",
        description="Grafite leve e áspero, bom para sombrear.",
        hardness=0.8,
        spacing=0.06,
        flow=0.35,
        grain=0.6,
        grain_scale=1.0,
    ),
    TipDefinition(
        key="watercolor",
        label="Aquarela",
        description="Borda difusa e translúcida que se acumula em camadas.",
        hardness=0.0,
        spacing=0.05,
        flow=0.28,
        grain=0.25,
        grain_scale=4.0,
        scatter=0.08,
    ),
)

TIPS_BY_KEY: dict[str, TipDefinition] = {tip.key: tip for tip in TIPS}

DEFAULT_TIP_KEY = "brush"


def get_tip(key: str) -> TipDefinition:
    """Ponta pelo identificador, caindo no pincel padrão se o nome for desconhecido."""
    return TIPS_BY_KEY.get(key, TIPS_BY_KEY[DEFAULT_TIP_KEY])


@dataclass
class StampRequest:
    """Tudo que muda de um carimbo para o outro dentro de um mesmo traço."""

    size: float
    offset_x: float = 0.0
    offset_y: float = 0.0
    angle: float | None = None
    rng: np.random.Generator = field(default_factory=np.random.default_rng)


def quantize_size(size: float) -> float:
    """Arredonda o tamanho para oitavos de pixel.

    Mantém o cache de máscaras eficaz sem que a diferença seja perceptível, e
    garante que o motor de traço e o renderizador cheguem sempre à mesma extensão.
    """
    return round(float(np.clip(size, MIN_SIZE, MAX_SIZE)) * 8) / 8


def render_stamp(tip: TipDefinition, request: StampRequest) -> np.ndarray:
    """Máscara alpha ``(n, n)`` do carimbo, já com o deslocamento subpixel aplicado."""
    size = quantize_size(request.size)
    angle = tip.angle if request.angle is None else request.angle

    if tip.shape == "spray":
        return _render_spray(tip, size, request)

    quantized_x = round(request.offset_x * SUBPIXEL_STEPS) / SUBPIXEL_STEPS
    quantized_y = round(request.offset_y * SUBPIXEL_STEPS) / SUBPIXEL_STEPS
    mask = _render_geometric(
        tip.shape,
        size,
        tip.hardness,
        tip.aspect,
        angle,
        quantized_x,
        quantized_y,
        tip.aliased,
    )

    if tip.grain > 0.0:
        mask = mask * _grain_texture(mask.shape[0], tip, request.rng)
    return mask


def stamp_extent(tip: TipDefinition, size: float) -> int:
    """Lado (em pixels) da matriz que comporta o carimbo."""
    return _extent(quantize_size(size))


def _extent(size: float) -> int:
    return int(np.ceil(size)) + 2


@lru_cache(maxsize=512)
def _render_geometric(
    shape: str,
    size: float,
    hardness: float,
    aspect: float,
    angle: float,
    offset_x: float,
    offset_y: float,
    aliased: bool,
) -> np.ndarray:
    extent = _extent(size)
    center = (extent - 1) / 2.0
    axis = np.arange(extent, dtype=np.float32)
    grid_x = axis[None, :] - center - np.float32(offset_x)
    grid_y = axis[:, None] - center - np.float32(offset_y)

    if angle:
        radians = np.deg2rad(angle, dtype=np.float32)
        cos_a, sin_a = np.cos(radians), np.sin(radians)
        grid_x, grid_y = (
            grid_x * cos_a + grid_y * sin_a,
            -grid_x * sin_a + grid_y * cos_a,
        )

    radius = max(size / 2.0, 0.5)
    normalized_x = grid_x / np.float32(radius)
    normalized_y = grid_y / np.float32(radius * max(aspect, 0.05))

    if shape == "square":
        distance = np.maximum(np.abs(normalized_x), np.abs(normalized_y))
    else:
        distance = np.sqrt(normalized_x**2 + normalized_y**2)

    if aliased:
        return (distance <= 1.0).astype(np.float32)

    # A borda precisa de pelo menos um pixel de transição, senão pinceis duros
    # ficam serrilhados; em pincéis macios a dureza é que manda.
    feather = max(1.0 / radius, 1.0 - hardness)
    alpha = np.clip((1.0 - distance) / feather, 0.0, 1.0).astype(np.float32)
    return alpha * alpha * (np.float32(3.0) - np.float32(2.0) * alpha)


def _render_spray(tip: TipDefinition, size: float, request: StampRequest) -> np.ndarray:
    """Nuvem de partículas com queda gaussiana a partir do centro."""
    extent = _extent(size)
    center = (extent - 1) / 2.0
    radius = max(size / 2.0, 0.5)

    particles = max(1, int(tip.density * radius * radius))
    angles = request.rng.uniform(0.0, 2.0 * np.pi, particles)
    # Raiz quadrada distribuiria uniformemente na área; o expoente maior
    # concentra o depósito no miolo, como um aerógrafo real.
    distances = radius * request.rng.random(particles) ** 0.7

    xs = np.rint(center + request.offset_x + distances * np.cos(angles)).astype(np.int32)
    ys = np.rint(center + request.offset_y + distances * np.sin(angles)).astype(np.int32)
    inside = (xs >= 0) & (xs < extent) & (ys >= 0) & (ys < extent)

    mask = np.zeros((extent, extent), dtype=np.float32)
    np.add.at(mask, (ys[inside], xs[inside]), np.float32(1.0))
    return np.minimum(mask, np.float32(1.0))


def _grain_texture(
    extent: int, tip: TipDefinition, rng: np.random.Generator
) -> np.ndarray:
    """Ruído multiplicativo que dá aspereza a giz, óleo e lápis natural."""
    coarse = max(2, int(extent / max(tip.grain_scale, 0.5)))
    noise = rng.random((coarse, coarse), dtype=np.float32)
    repeats = int(np.ceil(extent / coarse))
    tiled = np.repeat(np.repeat(noise, repeats, axis=0), repeats, axis=1)[:extent, :extent]
    return np.clip(np.float32(1.0) - tip.grain * tiled, 0.0, 1.0)
