"""Modos de pincel: o *efeito* aplicado sob a máscara, independente da forma.

Cada modo recebe a região original (RGBA ``float32`` em ``[0, 1]``) e a máscara
acumulada do traço, e devolve a região resultante. Como o modo nada sabe sobre a
ponta, qualquer ponta — inclusive o Spray — funciona com qualquer efeito.

Modos marcados como :attr:`BrushMode.sequential` são a exceção: eles dependem do
resultado do carimbo anterior (é o caso do blend, que arrasta pixels) e por isso
recebem a região *atual* em vez da original.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import color_ops
from .pixels import box_blur, composite_over


@dataclass(frozen=True)
class ModeDefinition:
    """Metadados de um efeito de pincel, para montar a interface."""

    key: str
    label: str
    description: str
    amount_label: str
    amount_min: int
    amount_max: int
    amount_default: int
    amount_suffix: str = "%"


MODE_DEFINITIONS: tuple[ModeDefinition, ...] = (
    ModeDefinition(
        key="paint",
        label="Pintar",
        description="Aplica a cor selecionada.",
        amount_label="Opacidade",
        amount_min=1,
        amount_max=100,
        amount_default=100,
    ),
    ModeDefinition(
        key="erase",
        label="Apagar",
        description="Remove pixels, deixando transparente ou a cor de fundo.",
        amount_label="Força",
        amount_min=1,
        amount_max=100,
        amount_default=100,
    ),
    ModeDefinition(
        key="saturation",
        label="Saturação",
        description="Satura ou dessatura apenas onde o pincel passa.",
        amount_label="Intensidade",
        amount_min=-100,
        amount_max=100,
        amount_default=40,
    ),
    ModeDefinition(
        key="blend",
        label="Blend",
        description="Arrasta e mistura as cores vizinhas, dissolvendo vincos e emendas.",
        amount_label="Força",
        amount_min=1,
        amount_max=100,
        amount_default=55,
    ),
    ModeDefinition(
        key="blur",
        label="Desfoque",
        description="Suaviza os detalhes da área pincelada.",
        amount_label="Intensidade",
        amount_min=1,
        amount_max=100,
        amount_default=60,
    ),
    ModeDefinition(
        key="sharpen",
        label="Nitidez",
        description="Realça bordas e microcontraste.",
        amount_label="Intensidade",
        amount_min=1,
        amount_max=100,
        amount_default=50,
    ),
    ModeDefinition(
        key="dodge",
        label="Clarear",
        description="Clareia progressivamente, preservando as altas luzes.",
        amount_label="Exposição",
        amount_min=1,
        amount_max=100,
        amount_default=35,
    ),
    ModeDefinition(
        key="burn",
        label="Escurecer",
        description="Escurece progressivamente, preservando as sombras.",
        amount_label="Exposição",
        amount_min=1,
        amount_max=100,
        amount_default=35,
    ),
    ModeDefinition(
        key="hue",
        label="Matiz",
        description="Gira a cor da área pincelada sem alterar o brilho.",
        amount_label="Giro",
        amount_min=-180,
        amount_max=180,
        amount_default=30,
        amount_suffix="°",
    ),
)

MODES_BY_KEY: dict[str, ModeDefinition] = {mode.key: mode for mode in MODE_DEFINITIONS}


class BrushMode:
    """Contrato de um efeito de pincel."""

    sequential: bool = False

    def apply(self, base: np.ndarray, mask: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class _RegionEffect(BrushMode):
    """Base dos efeitos que só transformam a cor, sem mexer no alpha."""

    def __init__(self, strength: float) -> None:
        self._strength = float(np.clip(strength, 0.0, 1.0))

    def transform(self, rgb: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def apply(self, base: np.ndarray, mask: np.ndarray) -> np.ndarray:
        weight = (mask * np.float32(self._strength))[..., None]
        result = base.copy()
        transformed = np.clip(self.transform(base[..., :3]), 0.0, 1.0)
        result[..., :3] = base[..., :3] + (transformed - base[..., :3]) * weight
        return result


class PaintMode(BrushMode):
    """Deposita a cor ativa usando *source-over*."""

    def __init__(self, color: np.ndarray, opacity: float) -> None:
        self._color = np.asarray(color, dtype=np.float32)
        self._opacity = float(np.clip(opacity, 0.0, 1.0))

    def apply(self, base: np.ndarray, mask: np.ndarray) -> np.ndarray:
        alpha = mask * np.float32(self._opacity * float(self._color[3]))
        return composite_over(base, self._color[:3], alpha)


class EraseMode(BrushMode):
    """Apaga para transparente ou repinta com a cor de fundo, como no Paint."""

    def __init__(self, strength: float, background: np.ndarray | None) -> None:
        self._strength = float(np.clip(strength, 0.0, 1.0))
        self._background = (
            None if background is None else np.asarray(background, dtype=np.float32)
        )

    def apply(self, base: np.ndarray, mask: np.ndarray) -> np.ndarray:
        alpha = mask * np.float32(self._strength)
        if self._background is not None:
            return composite_over(base, self._background[:3], alpha)
        result = base.copy()
        result[..., 3] = base[..., 3] * (np.float32(1.0) - alpha)
        return result


class SaturationMode(_RegionEffect):
    """Satura (``amount`` > 0) ou dessatura a área pincelada.

    ``amount`` vai de -1 a +1: -1 zera a cor, +1 triplica a distância até o cinza.
    """

    def __init__(self, amount: float, strength: float = 1.0) -> None:
        super().__init__(strength)
        clamped = float(np.clip(amount, -1.0, 1.0))
        self._factor = 1.0 + clamped * (2.0 if clamped >= 0.0 else 1.0)

    def transform(self, rgb: np.ndarray) -> np.ndarray:
        return color_ops.adjust_saturation(rgb, self._factor)


class HueMode(_RegionEffect):
    """Gira o matiz da área pincelada. ``degrees`` em ``[-180, 180]``."""

    def __init__(self, degrees: float, strength: float = 1.0) -> None:
        super().__init__(strength)
        self._degrees = float(degrees)

    def transform(self, rgb: np.ndarray) -> np.ndarray:
        return color_ops.adjust_hue(rgb, self._degrees)


class BlurMode(_RegionEffect):
    """Desfoca a área pincelada. O raio acompanha o tamanho do pincel."""

    def __init__(self, amount: float, brush_size: float, strength: float = 1.0) -> None:
        super().__init__(strength)
        self._radius = max(1, int(round(amount * max(brush_size, 4.0) * 0.12)))

    def apply(self, base: np.ndarray, mask: np.ndarray) -> np.ndarray:
        blurred = box_blur(base, self._radius)
        weight = (mask * np.float32(self._strength))[..., None]
        result = base.copy()
        result[..., :3] = base[..., :3] + (blurred[..., :3] - base[..., :3]) * weight
        return result

    def transform(self, rgb: np.ndarray) -> np.ndarray:  # pragma: no cover - não usado
        return rgb


class SharpenMode(BrushMode):
    """Máscara de nitidez local: realça o que difere da versão desfocada."""

    def __init__(self, amount: float, strength: float = 1.0) -> None:
        self._amount = float(np.clip(amount, 0.0, 1.0)) * 2.0
        self._strength = float(np.clip(strength, 0.0, 1.0))

    def apply(self, base: np.ndarray, mask: np.ndarray) -> np.ndarray:
        blurred = box_blur(base, 1)
        detail = base[..., :3] - blurred[..., :3]
        sharpened = np.clip(base[..., :3] + detail * np.float32(self._amount), 0.0, 1.0)
        weight = (mask * np.float32(self._strength))[..., None]
        result = base.copy()
        result[..., :3] = base[..., :3] + (sharpened - base[..., :3]) * weight
        return result


class DodgeMode(_RegionEffect):
    """Clareia sem estourar: quanto mais claro o pixel, menos ele sobe."""

    def __init__(self, amount: float, strength: float = 1.0) -> None:
        super().__init__(strength)
        self._amount = np.float32(np.clip(amount, 0.0, 1.0))

    def transform(self, rgb: np.ndarray) -> np.ndarray:
        return color_ops.blend_dodge(rgb, self._amount)


class BurnMode(_RegionEffect):
    """Escurece sem empastar: quanto mais escuro o pixel, menos ele desce."""

    def __init__(self, amount: float, strength: float = 1.0) -> None:
        super().__init__(strength)
        self._amount = np.float32(np.clip(amount, 0.0, 1.0))

    def transform(self, rgb: np.ndarray) -> np.ndarray:
        return color_ops.blend_burn(rgb, self._amount)


class BlendSmudgeMode(BrushMode):
    """Arrasta cor de onde o pincel esteve para onde ele está.

    Mantém um acumulador do tamanho do carimbo que "pega" cor a cada passo e a
    solta adiante — é o que dissolve vincos e emendas em vez de apenas borrar.
    Por depender do carimbo anterior, é o único modo sequencial.
    """

    sequential = True

    def __init__(self, strength: float) -> None:
        self._strength = float(np.clip(strength, 0.02, 1.0))
        self._carry: np.ndarray | None = None

    def apply(self, current: np.ndarray, mask: np.ndarray) -> np.ndarray:
        if self._carry is None or self._carry.shape != current.shape:
            self._carry = current.copy()

        pickup = np.float32(1.0 - self._strength * 0.75)
        self._carry = self._carry * pickup + current * np.float32(1.0 - pickup)

        weight = (mask * np.float32(self._strength))[..., None]
        return current + (self._carry - current) * weight
