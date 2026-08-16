"""Operações de cor vetorizadas.

Todas as funções recebem e devolvem RGB em ``float32`` normalizado em ``[0, 1]``,
com shape ``(..., 3)``. Nenhuma delas satura o resultado: o clamp fica a cargo de
quem compõe o pipeline, para que ajustes encadeados não percam informação a cada
etapa intermediária.
"""

from __future__ import annotations

import numpy as np

LUMA_WEIGHTS = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

SEPIA_MATRIX = np.array(
    [
        [0.393, 0.769, 0.189],
        [0.349, 0.686, 0.168],
        [0.272, 0.534, 0.131],
    ],
    dtype=np.float32,
)


def luminance(rgb: np.ndarray) -> np.ndarray:
    """Luminância perceptual (Rec. 709), shape ``(...)``."""
    return rgb @ LUMA_WEIGHTS


def adjust_saturation(rgb: np.ndarray, factor: float) -> np.ndarray:
    """Escala a distância de cada pixel até seu cinza equivalente.

    ``factor`` 0 devolve escala de cinza, 1 não altera nada e valores acima de 1
    intensificam. Valores negativos invertem a cor em torno do cinza.
    """
    if factor == 1.0:
        return rgb
    gray = luminance(rgb)[..., None]
    return gray + (rgb - gray) * np.float32(factor)


def adjust_vibrance(rgb: np.ndarray, amount: float) -> np.ndarray:
    """Satura mais os pixels apagados e poupa os que já estão vivos.

    ``amount`` vai de -1 (dessatura) a +1 (satura). Diferente de
    :func:`adjust_saturation`, protege tons de pele e evita estourar cores que já
    estavam no limite.
    """
    if amount == 0.0:
        return rgb
    gray = luminance(rgb)[..., None]
    deviation = rgb - gray
    current = np.abs(deviation).max(axis=-1, keepdims=True) * np.float32(2.0)
    weight = np.clip(np.float32(1.0) - current, 0.0, 1.0)
    return gray + deviation * (np.float32(1.0) + np.float32(amount) * weight)


def adjust_brightness(rgb: np.ndarray, amount: float) -> np.ndarray:
    """Desloca todos os canais linearmente. ``amount`` em ``[-1, 1]``."""
    if amount == 0.0:
        return rgb
    return rgb + np.float32(amount)


def adjust_contrast(rgb: np.ndarray, factor: float) -> np.ndarray:
    """Expande ou comprime em torno do cinza médio. ``factor`` 1 = neutro."""
    if factor == 1.0:
        return rgb
    return (rgb - np.float32(0.5)) * np.float32(factor) + np.float32(0.5)


def adjust_exposure(rgb: np.ndarray, stops: float) -> np.ndarray:
    """Multiplica por ``2 ** stops``, imitando pontos de exposição fotográfica."""
    if stops == 0.0:
        return rgb
    return rgb * np.float32(2.0**stops)


def adjust_gamma(rgb: np.ndarray, gamma: float) -> np.ndarray:
    """Curva de potência; ``gamma`` < 1 clareia os meios-tons."""
    if gamma == 1.0:
        return rgb
    return np.power(np.clip(rgb, 0.0, 1.0), np.float32(gamma))


def hue_rotation_matrix(degrees: float) -> np.ndarray:
    """Matriz 3x3 que gira o matiz preservando a luminância."""
    radians = np.deg2rad(degrees, dtype=np.float32)
    cos_a = float(np.cos(radians))
    sin_a = float(np.sin(radians))
    return np.array(
        [
            [
                0.299 + 0.701 * cos_a + 0.168 * sin_a,
                0.587 - 0.587 * cos_a + 0.330 * sin_a,
                0.114 - 0.114 * cos_a - 0.497 * sin_a,
            ],
            [
                0.299 - 0.299 * cos_a - 0.328 * sin_a,
                0.587 + 0.413 * cos_a + 0.035 * sin_a,
                0.114 - 0.114 * cos_a + 0.292 * sin_a,
            ],
            [
                0.299 - 0.300 * cos_a + 1.250 * sin_a,
                0.587 - 0.588 * cos_a - 1.050 * sin_a,
                0.114 + 0.886 * cos_a - 0.203 * sin_a,
            ],
        ],
        dtype=np.float32,
    )


def adjust_hue(rgb: np.ndarray, degrees: float) -> np.ndarray:
    """Gira o matiz em graus, mantendo luminância aproximadamente constante."""
    if degrees % 360.0 == 0.0:
        return rgb
    return rgb @ hue_rotation_matrix(degrees).T


def adjust_temperature(rgb: np.ndarray, amount: float) -> np.ndarray:
    """Esquenta (``amount`` > 0, mais vermelho) ou esfria (mais azul).

    ``amount`` em ``[-1, 1]``; o verde fica intocado para não virar dominante de cor.
    """
    if amount == 0.0:
        return rgb
    shift = np.float32(amount) * np.float32(0.25)
    scale = np.array([1.0 + shift, 1.0, 1.0 - shift], dtype=np.float32)
    return rgb * scale


def adjust_tint(rgb: np.ndarray, amount: float) -> np.ndarray:
    """Desloca o eixo verde/magenta. ``amount`` > 0 puxa para magenta."""
    if amount == 0.0:
        return rgb
    shift = np.float32(amount) * np.float32(0.25)
    scale = np.array([1.0 + shift * 0.5, 1.0 - shift, 1.0 + shift * 0.5], dtype=np.float32)
    return rgb * scale


def to_grayscale(rgb: np.ndarray) -> np.ndarray:
    """Substitui cada pixel pela sua luminância."""
    return np.repeat(luminance(rgb)[..., None], 3, axis=-1)


def invert(rgb: np.ndarray) -> np.ndarray:
    """Negativo fotográfico."""
    return np.float32(1.0) - rgb


def to_sepia(rgb: np.ndarray) -> np.ndarray:
    """Viragem sépia clássica."""
    return rgb @ SEPIA_MATRIX.T


def posterize(rgb: np.ndarray, levels: int) -> np.ndarray:
    """Reduz cada canal a ``levels`` degraus discretos."""
    if levels >= 256:
        return rgb
    steps = np.float32(max(2, levels) - 1)
    return np.round(np.clip(rgb, 0.0, 1.0) * steps) / steps


def tonal_curve(values: np.ndarray, amount: float) -> np.ndarray:
    """Afasta (ou aproxima) claros e escuros sem estourar os extremos.

    ``amount`` positivo mistura a entrada com uma curva em S (``smoothstep``):
    os meios-tons se separam enquanto branco e preto ficam onde estão — o
    contraste linear, por comparação, empurra tudo e ceifa os extremos.
    ``amount`` negativo achata a faixa em direção ao cinza médio.

    As duas curvas são monotônicas, então nenhuma inversão de tom aparece por
    mais que a ferramenta seja repassada.
    """
    if amount == 0.0:
        return values
    clamped = np.clip(values, 0.0, 1.0)
    if amount > 0.0:
        curved = clamped * clamped * (np.float32(3.0) - np.float32(2.0) * clamped)
        weight = np.float32(min(amount, 1.0))
    else:
        curved = np.float32(0.5) + (clamped - np.float32(0.5)) * np.float32(0.35)
        weight = np.float32(min(-amount, 1.0))
    return clamped + (curved - clamped) * weight


def apply_to_luminance(rgb: np.ndarray, target_luminance: np.ndarray) -> np.ndarray:
    """Reescala o RGB para atingir uma luminância alvo, preservando o matiz.

    Mexer nos canais um a um giraria a cor junto com o tom; escalar todos pelo
    mesmo fator muda só o brilho, que é o que uma ferramenta tonal deve fazer.
    """
    current = luminance(rgb)[..., None]
    safe = np.where(current > 1e-4, current, np.float32(1.0))
    return rgb * (target_luminance[..., None] / safe)


def blend_dodge(rgb: np.ndarray, strength: np.ndarray) -> np.ndarray:
    """Clareia preservando as altas luzes (``color dodge`` suavizado)."""
    return rgb + (np.float32(1.0) - rgb) * strength


def blend_burn(rgb: np.ndarray, strength: np.ndarray) -> np.ndarray:
    """Escurece preservando as sombras (``color burn`` suavizado)."""
    return rgb * (np.float32(1.0) - strength)
