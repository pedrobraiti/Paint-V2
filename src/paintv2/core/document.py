"""O documento em edição: buffer de pixels, histórico e transformações.

O buffer é sempre ``uint8`` RGBA não-premultiplicado e **contíguo em C** — é essa
garantia que permite ao Qt criar um ``QImage`` apontando para a mesma memória,
sem cópia, a cada quadro desenhado na tela.

Este módulo não importa Qt: entrada e saída de arquivo passam pelo Pillow, o que
mantém todo o núcleo testável sem abrir janela.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .adjustments import AdjustmentSettings, apply_adjustments
from .history import History, PatchEntry, ReplaceEntry
from .pixels import Rect, clip_rect, view
from .stroke import StrokeBuffers

MAX_DIMENSION = 20000
WHITE = (255, 255, 255, 255)

READABLE_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".ico",
)
WRITABLE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp")

_EXTENSION_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".bmp": "BMP",
    ".tif": "TIFF",
    ".tiff": "TIFF",
    ".webp": "WEBP",
}
_FLATTEN_FORMATS = {"JPEG", "BMP"}


class Document:
    """Uma imagem aberta para edição, com desfazer/refazer próprio."""

    def __init__(
        self,
        pixels: np.ndarray,
        path: Path | None = None,
        name: str | None = None,
    ) -> None:
        self._pixels = np.ascontiguousarray(pixels, dtype=np.uint8)
        self.path = path
        self._name = name
        self.history = History()
        self.stroke_buffers = StrokeBuffers(*self._pixels.shape[:2])
        self.is_dirty = False

    # ------------------------------------------------------------------ criação

    @classmethod
    def blank(
        cls, width: int, height: int, color: tuple[int, int, int, int] = WHITE
    ) -> Document:
        """Tela em branco preenchida com ``color``."""
        width = max(1, min(int(width), MAX_DIMENSION))
        height = max(1, min(int(height), MAX_DIMENSION))
        pixels = np.empty((height, width, 4), dtype=np.uint8)
        pixels[:] = np.asarray(color, dtype=np.uint8)
        return cls(pixels)

    @classmethod
    def open(cls, path: str | Path) -> Document:
        """Carrega um arquivo de imagem, respeitando a orientação EXIF."""
        resolved = Path(path)
        with Image.open(resolved) as image:
            oriented = ImageOps.exif_transpose(image)
            pixels = np.array(oriented.convert("RGBA"), dtype=np.uint8)
        return cls(pixels, path=resolved)

    # ------------------------------------------------------------- propriedades

    @property
    def pixels(self) -> np.ndarray:
        return self._pixels

    @property
    def width(self) -> int:
        return self._pixels.shape[1]

    @property
    def height(self) -> int:
        return self._pixels.shape[0]

    @property
    def name(self) -> str:
        if self._name:
            return self._name
        return self.path.name if self.path else "Sem título"

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def bounds(self) -> Rect:
        return 0, 0, self.width, self.height

    def replace_pixels(self, pixels: np.ndarray) -> None:
        """Troca o buffer inteiro (usado por redimensionar, girar e recortar)."""
        self._pixels = np.ascontiguousarray(pixels, dtype=np.uint8)
        if not self.stroke_buffers.matches(*self._pixels.shape[:2]):
            self.stroke_buffers = StrokeBuffers(*self._pixels.shape[:2])
        self.is_dirty = True

    # ----------------------------------------------------------------- histórico

    def snapshot_region(self, rect: Rect) -> np.ndarray | None:
        """Cópia dos pixels de ``rect``, para servir de "antes" num patch."""
        clipped = clip_rect(rect, self.width, self.height)
        if clipped is None:
            return None
        return view(self._pixels, clipped).copy()

    def commit_patch(self, label: str, rect: Rect, before: np.ndarray) -> None:
        """Registra no histórico uma alteração já escrita no buffer."""
        clipped = clip_rect(rect, self.width, self.height)
        if clipped is None:
            return
        self.history.push(
            PatchEntry(label, clipped, before, view(self._pixels, clipped).copy())
        )
        self.is_dirty = True

    def commit_replace(self, label: str, before: np.ndarray) -> None:
        """Registra a substituição integral do buffer."""
        self.history.push(ReplaceEntry(label, before, self._pixels.copy()))
        self.is_dirty = True

    def undo(self) -> bool:
        if self.history.undo(self) is None:
            return False
        self.is_dirty = True
        return True

    def redo(self) -> bool:
        if self.history.redo(self) is None:
            return False
        self.is_dirty = True
        return True

    # ------------------------------------------------------------ transformações

    def resize(self, width: int, height: int, smooth: bool = True) -> None:
        """Redimensiona a imagem inteira."""
        width = max(1, min(int(width), MAX_DIMENSION))
        height = max(1, min(int(height), MAX_DIMENSION))
        if (width, height) == (self.width, self.height):
            return
        before = self._pixels.copy()
        resample = Image.LANCZOS if smooth else Image.NEAREST
        resized = Image.fromarray(self._pixels, mode="RGBA").resize(
            (width, height), resample
        )
        self.replace_pixels(np.array(resized, dtype=np.uint8))
        self.commit_replace("Redimensionar", before)

    def crop(self, rect: Rect) -> None:
        """Recorta para ``rect`` (coordenadas do documento)."""
        clipped = clip_rect(rect, self.width, self.height)
        if clipped is None or clipped[2:] == (self.width, self.height):
            return
        before = self._pixels.copy()
        self.replace_pixels(view(self._pixels, clipped).copy())
        self.commit_replace("Recortar", before)

    def rotate(self, degrees: float) -> None:
        """Gira no sentido horário, expandindo a tela quando necessário."""
        if degrees % 360 == 0:
            return
        before = self._pixels.copy()
        rotated = Image.fromarray(self._pixels, mode="RGBA").rotate(
            -degrees, expand=True, resample=Image.BICUBIC
        )
        self.replace_pixels(np.array(rotated, dtype=np.uint8))
        self.commit_replace("Girar", before)

    def flip(self, horizontal: bool) -> None:
        """Espelha na horizontal ou na vertical."""
        before = self._pixels.copy()
        axis = 1 if horizontal else 0
        self.replace_pixels(np.flip(self._pixels, axis=axis))
        self.commit_replace("Inverter", before)

    def expand_canvas(self, width: int, height: int, color=WHITE) -> None:
        """Aumenta a tela sem escalar o conteúdo, ancorado no canto superior esquerdo."""
        width = max(1, min(int(width), MAX_DIMENSION))
        height = max(1, min(int(height), MAX_DIMENSION))
        if (width, height) == (self.width, self.height):
            return
        before = self._pixels.copy()
        canvas = np.empty((height, width, 4), dtype=np.uint8)
        canvas[:] = np.asarray(color, dtype=np.uint8)
        copy_height = min(height, self.height)
        copy_width = min(width, self.width)
        canvas[:copy_height, :copy_width] = self._pixels[:copy_height, :copy_width]
        self.replace_pixels(canvas)
        self.commit_replace("Tamanho da tela", before)

    def apply_adjustments(
        self,
        settings: AdjustmentSettings,
        rect: Rect | None = None,
        mask: np.ndarray | None = None,
    ) -> Rect | None:
        """Aplica ajustes ao documento, a ``rect``, ou só aos pixels de ``mask``."""
        target = clip_rect(rect or self.bounds, self.width, self.height)
        if target is None or settings.is_identity:
            return None
        before = view(self._pixels, target).copy()
        adjusted = apply_adjustments(before, settings)
        if mask is not None:
            adjusted = np.where(view(mask, target)[..., None], adjusted, before)
        view(self._pixels, target)[:] = adjusted
        self.commit_patch("Ajustes de imagem", target, before)
        return target

    # ------------------------------------------------------------------- arquivo

    def save(self, path: str | Path | None = None, quality: int = 95) -> Path:
        """Grava no disco, achatando o alpha quando o formato não o suporta."""
        destination = Path(path) if path else self.path
        if destination is None:
            raise ValueError("Documento sem caminho de destino.")

        suffix = destination.suffix.lower()
        image_format = _EXTENSION_FORMATS.get(suffix, "PNG")
        image = Image.fromarray(self._pixels, mode="RGBA")

        if image_format in _FLATTEN_FORMATS:
            background = Image.new("RGBA", image.size, WHITE)
            image = Image.alpha_composite(background, image).convert("RGB")

        destination.parent.mkdir(parents=True, exist_ok=True)
        save_options = {"quality": quality} if image_format in {"JPEG", "WEBP"} else {}
        image.save(destination, format=image_format, **save_options)

        self.path = destination
        self._name = None
        self.is_dirty = False
        return destination
