"""Gera o ícone do aplicativo.

A identidade é o Paint "em negativo": onde o ícone original é claro com azul, o
Paint-V2 é grafite com âmbar (o complemento exato do azul do Windows), e os
respingos de tinta usam as cores invertidas das do original — vermelho vira
ciano, amarelo vira azul, azul vira amarelo, verde vira magenta.

Desenha em alta resolução e reduz para cada tamanho, o que dá antisserrilhado
melhor do que desenhar direto em 16×16.

Uso:
    python scripts/build_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

CANVAS = 1024
ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "src" / "paintv2" / "resources"

BACKGROUND_TOP = (36, 40, 51)
BACKGROUND_BOTTOM = (16, 18, 23)
PALETTE_BODY = (255, 159, 69)
PALETTE_SHADE = (214, 122, 42)
THUMB_HOLE = (20, 22, 27)
BRUSH_HANDLE = (236, 238, 245)
BRUSH_FERRULE = (150, 158, 176)
BRUSH_TIP = (76, 194, 255)

BLOBS = (
    ((300, 330), 78, (43, 232, 232)),   # inverso do vermelho
    ((520, 268), 74, (76, 107, 255)),   # inverso do amarelo
    ((712, 372), 70, (255, 212, 59)),   # inverso do azul
    ((262, 592), 68, (255, 92, 216)),   # inverso do verde
)


def vertical_gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]):
    """Fundo em degradê, para o ícone não ficar chapado nos tamanhos grandes."""
    ramp = np.linspace(0.0, 1.0, size, dtype=np.float32)[:, None]
    colors = np.array(top, dtype=np.float32) * (1.0 - ramp) + np.array(
        bottom, dtype=np.float32
    ) * ramp
    pixels = np.repeat(colors[:, None, :], size, axis=1).astype(np.uint8)
    return Image.fromarray(pixels, mode="RGB").convert("RGBA")


def rounded_mask(size: int, radius_ratio: float = 0.22) -> Image.Image:
    """Máscara com os cantos arredondados no estilo dos ícones do Windows 11."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=int(size * radius_ratio), fill=255
    )
    return mask


def draw_palette(draw: ImageDraw.ImageDraw) -> None:
    """A paleta de pintor, com sombra inferior para dar volume."""
    draw.ellipse((150, 190, 880, 780), fill=PALETTE_SHADE)
    draw.ellipse((150, 170, 880, 750), fill=PALETTE_BODY)
    draw.ellipse((610, 480, 810, 660), fill=THUMB_HOLE)


def draw_blobs(draw: ImageDraw.ImageDraw) -> None:
    for (center_x, center_y), radius, color in BLOBS:
        draw.ellipse(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            fill=color,
        )


def draw_brush(base: Image.Image) -> None:
    """Pincel na diagonal, desenhado numa camada girada para ficar limpo."""
    layer = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    draw.rounded_rectangle((470, 120, 560, 520), radius=44, fill=BRUSH_HANDLE)
    draw.rectangle((470, 520, 560, 600), fill=BRUSH_FERRULE)
    draw.polygon(
        [(470, 600), (560, 600), (536, 736), (494, 736)],
        fill=BRUSH_TIP,
    )

    rotated = layer.rotate(-34, resample=Image.BICUBIC, center=(515, 430))
    base.alpha_composite(rotated.transform(
        (CANVAS, CANVAS), Image.AFFINE, (1, 0, 40, 0, 1, 90), resample=Image.BICUBIC
    ))


def render_icon() -> Image.Image:
    icon = vertical_gradient(CANVAS, BACKGROUND_TOP, BACKGROUND_BOTTOM)
    icon.putalpha(rounded_mask(CANVAS))

    artwork = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(artwork)
    draw_palette(draw)
    draw_blobs(draw)
    icon.alpha_composite(artwork)

    draw_brush(icon)
    return icon


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    icon = render_icon()

    png_path = OUTPUT_DIR / "paintv2.png"
    icon.resize((512, 512), Image.LANCZOS).save(png_path, format="PNG")

    ico_path = OUTPUT_DIR / "paintv2.ico"
    icon.save(
        ico_path,
        format="ICO",
        sizes=[(size, size) for size in ICO_SIZES],
    )

    print(f"Ícone gerado em {ico_path} e {png_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
