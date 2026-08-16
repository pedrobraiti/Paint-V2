"""Ajustes globais de imagem, aplicados ao documento inteiro ou a uma seleção.

A ordem das etapas segue o fluxo de um revelador fotográfico: primeiro o que é
tonal (exposição, brilho, contraste), depois o que é de cor (temperatura, matiz,
saturação) e só então as viragens criativas. Inverter essa ordem mudaria o
resultado — contraste aplicado depois da saturação, por exemplo, reintroduz
estouro de cor que a saturação já havia contido.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

import numpy as np

from . import color_ops
from .pixels import to_float, to_uint8


@dataclass
class AdjustmentSettings:
    """Parâmetros dos ajustes globais, todos neutros por padrão."""

    exposure: float = 0.0
    brightness: float = 0.0
    contrast: float = 0.0
    temperature: float = 0.0
    tint: float = 0.0
    hue: float = 0.0
    saturation: float = 0.0
    vibrance: float = 0.0
    grayscale: bool = False
    sepia: bool = False
    invert: bool = False
    posterize: int = 0

    @property
    def is_identity(self) -> bool:
        """Se nada muda, o chamador pode pular o processamento por completo."""
        defaults = AdjustmentSettings()
        return all(
            getattr(self, field.name) == getattr(defaults, field.name)
            for field in fields(self)
        )

    def reset(self) -> None:
        for field in fields(self):
            setattr(self, field.name, field.default)


def apply_adjustments(pixels: np.ndarray, settings: AdjustmentSettings) -> np.ndarray:
    """Devolve uma cópia ``uint8`` RGBA de ``pixels`` com os ajustes aplicados."""
    if settings.is_identity:
        return pixels.copy()

    result = to_float(pixels)
    rgb = result[..., :3]

    rgb = color_ops.adjust_exposure(rgb, settings.exposure / 50.0)
    rgb = color_ops.adjust_brightness(rgb, settings.brightness / 100.0)
    rgb = color_ops.adjust_contrast(rgb, 1.0 + settings.contrast / 100.0)
    rgb = color_ops.adjust_temperature(rgb, settings.temperature / 100.0)
    rgb = color_ops.adjust_tint(rgb, settings.tint / 100.0)
    rgb = color_ops.adjust_hue(rgb, settings.hue)
    rgb = color_ops.adjust_saturation(rgb, 1.0 + settings.saturation / 100.0)
    rgb = color_ops.adjust_vibrance(rgb, settings.vibrance / 100.0)

    if settings.grayscale:
        rgb = color_ops.to_grayscale(rgb)
    if settings.sepia:
        rgb = color_ops.to_sepia(rgb)
    if settings.invert:
        rgb = color_ops.invert(rgb)
    if settings.posterize:
        rgb = color_ops.posterize(rgb, settings.posterize)

    result[..., :3] = np.clip(rgb, 0.0, 1.0)
    return to_uint8(result)
