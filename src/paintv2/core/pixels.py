"""Conversões e composição de pixels RGBA.

O documento inteiro vive como ``uint8`` RGBA não-premultiplicado — é o formato que
o Qt consegue enxergar diretamente na memória do NumPy, sem cópia. Já os cálculos
de cor precisam de ``float32``, então as conversões abaixo são a fronteira entre
os dois mundos e ficam concentradas aqui.
"""

from __future__ import annotations

import numpy as np

Rect = tuple[int, int, int, int]
"""Retângulo ``(x, y, largura, altura)`` em pixels do documento."""


def to_float(pixels: np.ndarray) -> np.ndarray:
    """``uint8`` 0..255 para ``float32`` 0..1.

    A escala acontece no lugar, sobre o array recém-convertido: no caminho quente
    do pincel cada temporário a menos é um megabyte a menos de tráfego de memória
    por carimbo.
    """
    result = pixels.astype(np.float32)
    result *= np.float32(1.0 / 255.0)
    return result


def to_uint8(pixels: np.ndarray) -> np.ndarray:
    """``float32`` 0..1 para ``uint8`` 0..255, com clamp e arredondamento."""
    scaled = np.clip(pixels, 0.0, 1.0)
    scaled *= np.float32(255.0)
    scaled += np.float32(0.5)
    return scaled.astype(np.uint8)


def clip_rect(rect: Rect, width: int, height: int) -> Rect | None:
    """Recorta ``rect`` aos limites do documento; ``None`` se nada sobrar."""
    x, y, w, h = rect
    left = max(0, x)
    top = max(0, y)
    right = min(width, x + w)
    bottom = min(height, y + h)
    if right <= left or bottom <= top:
        return None
    return left, top, right - left, bottom - top


def union_rect(first: Rect | None, second: Rect | None) -> Rect | None:
    """Menor retângulo que contém os dois."""
    if first is None:
        return second
    if second is None:
        return first
    left = min(first[0], second[0])
    top = min(first[1], second[1])
    right = max(first[0] + first[2], second[0] + second[2])
    bottom = max(first[1] + first[3], second[1] + second[3])
    return left, top, right - left, bottom - top


def view(pixels: np.ndarray, rect: Rect) -> np.ndarray:
    """Fatia (sem cópia) do buffer correspondente ao retângulo."""
    x, y, w, h = rect
    return pixels[y : y + h, x : x + w]


def composite_over(base: np.ndarray, src_rgb: np.ndarray, src_alpha: np.ndarray) -> np.ndarray:
    """Compõe ``src`` sobre ``base`` (ambos RGBA float32, alpha não-premultiplicado).

    Implementa o operador *source-over* de Porter-Duff. ``src_alpha`` tem shape
    ``(h, w)`` e ``src_rgb`` pode ser ``(3,)`` (cor sólida) ou ``(h, w, 3)``.
    """
    base_alpha = base[..., 3]
    src_a = src_alpha
    out_alpha = src_a + base_alpha * (np.float32(1.0) - src_a)

    # Onde o resultado é totalmente transparente não há cor a preservar; o
    # divisor vira 1 só para não gerar divisão por zero.
    safe_alpha = np.where(out_alpha > 0.0, out_alpha, np.float32(1.0))
    weighted_src = src_rgb * src_a[..., None]
    weighted_base = base[..., :3] * (base_alpha * (np.float32(1.0) - src_a))[..., None]

    result = np.empty_like(base)
    result[..., :3] = (weighted_src + weighted_base) / safe_alpha[..., None]
    result[..., 3] = out_alpha
    return result


def lerp_rgba(base: np.ndarray, target: np.ndarray, weight: np.ndarray) -> np.ndarray:
    """Interpola RGBA entre ``base`` e ``target`` com peso por pixel ``(h, w)``."""
    factor = weight[..., None]
    return base + (target - base) * factor


def box_blur(image: np.ndarray, radius: int) -> np.ndarray:
    """Desfoque de caixa separável via soma acumulada — O(n) no raio.

    Trabalha com RGB premultiplicado pelo alpha para que pixels transparentes não
    contaminem os vizinhos com sua cor arbitrária. Quando a região é toda opaca —
    o caso comum ao retocar uma foto — os dois passes de premultiplicação são
    puro desperdício e por isso ficam de fora.
    """
    if radius < 1:
        return image

    opaque = bool((image[..., 3] >= 1.0).all())
    working = image if opaque else image.copy()
    if not opaque:
        working[..., :3] *= working[..., 3:4]

    blurred = _box_blur_axis(_box_blur_axis(working, radius, axis=1), radius, axis=0)

    if not opaque:
        alpha = blurred[..., 3:4]
        blurred[..., :3] /= np.where(alpha > 1e-6, alpha, np.float32(1.0))
    return blurred


def _axis_slice(array: np.ndarray, axis: int, start: int, stop: int) -> np.ndarray:
    """Fatia ao longo de um eixo qualquer — uma vista, sem cópia."""
    selector: list[slice] = [slice(None)] * array.ndim
    selector[axis] = slice(start, stop)
    return array[tuple(selector)]


def _box_blur_axis(image: np.ndarray, radius: int, axis: int) -> np.ndarray:
    """Média móvel ao longo de um eixo, com bordas estendidas por replicação."""
    length = image.shape[axis]
    span = min(radius, max(0, length - 1))
    if span < 1:
        return image

    padding = [(0, 0)] * image.ndim
    padding[axis] = (span + 1, span)
    padded = np.pad(image, padding, mode="edge")
    # A primeira linha do preenchimento é zerada para servir de origem da soma
    # acumulada, o que evita concatenar um bloco de zeros depois.
    _axis_slice(padded, axis, 0, 1)[:] = 0.0
    cumulative = np.cumsum(padded, axis=axis, dtype=np.float32)

    window = 2 * span + 1
    result = _axis_slice(cumulative, axis, window, window + length) - _axis_slice(
        cumulative, axis, 0, length
    )
    result *= np.float32(1.0 / window)
    return result
