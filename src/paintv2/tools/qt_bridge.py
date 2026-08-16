"""Ponte entre o buffer NumPy do documento e o desenho vetorial do Qt.

Formas, texto e colagem são muito mais simples (e antisserrilhados de graça) se
desenhados com ``QPainter``. Como o ``QImage`` aponta para a mesma memória do
array NumPy, esse desenho cai direto no documento — sem conversão, sem cópia.
"""

from __future__ import annotations

from contextlib import contextmanager

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter, QPainterPath

from ..core.document import Document
from ..core.pixels import Rect
from ..core.selection import Selection

IMAGE_FORMAT = QImage.Format.Format_RGBA8888


def image_over(pixels: np.ndarray) -> QImage:
    """``QImage`` que compartilha a memória do array (nenhuma cópia é feita)."""
    height, width = pixels.shape[:2]
    return QImage(pixels.data, width, height, pixels.strides[0], IMAGE_FORMAT)


def document_image(document: Document) -> QImage:
    return image_over(document.pixels)


def image_to_array(image: QImage) -> np.ndarray:
    """Cópia ``uint8`` RGBA de um ``QImage`` qualquer (usada na colagem)."""
    converted = image.convertToFormat(IMAGE_FORMAT)
    width, height = converted.width(), converted.height()
    buffer = converted.constBits()
    array = np.frombuffer(buffer, dtype=np.uint8, count=height * converted.bytesPerLine())
    array = array.reshape(height, converted.bytesPerLine() // 4, 4)
    return np.ascontiguousarray(array[:, :width])


def array_to_image(pixels: np.ndarray) -> QImage:
    """``QImage`` independente (com cópia) a partir de um array RGBA."""
    return image_over(np.ascontiguousarray(pixels)).copy()


def rasterize_path(path: QPainterPath, width: int, height: int) -> np.ndarray:
    """Converte um caminho fechado numa máscara booleana do tamanho do documento."""
    image = QImage(width, height, QImage.Format.Format_Grayscale8)
    image.fill(0)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(Qt.GlobalColor.white)
    painter.drawPath(path)
    painter.end()

    stride = image.bytesPerLine()
    flat = np.frombuffer(image.constBits(), dtype=np.uint8, count=height * stride)
    return flat.reshape(height, stride)[:, :width] > 127


@contextmanager
def painter_for(document: Document, selection: Selection, antialias: bool):
    """``QPainter`` pronto para desenhar no documento, respeitando a seleção.

    É um gerenciador de contexto de propósito: o ``QImage`` que serve de destino
    precisa continuar vivo enquanto o pintor existir, e prendê-lo ao escopo do
    ``with`` é o que garante isso.
    """
    image = document_image(document)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, antialias)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, antialias)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, antialias)
    if selection.is_active and selection.bounds is not None:
        painter.setClipPath(_selection_clip(selection))
    try:
        yield painter
    finally:
        painter.end()


def _selection_clip(selection: Selection) -> QPainterPath:
    """Aproxima a seleção por retângulos de linha — exato e barato o bastante.

    Um caminho por pixel seria inviável; agrupar cada linha em segmentos
    contíguos dá o mesmo recorte com poucas centenas de retângulos.
    """
    path = QPainterPath()
    mask = selection.mask
    if mask is None:
        return path
    x, y, width, height = selection.bounds
    for row in range(y, y + height):
        line = mask[row, x : x + width]
        if not line.any():
            continue
        # O preenchimento com False nas duas pontas garante que as transições
        # saiam sempre em pares (início, fim) de segmento.
        edges = np.flatnonzero(np.diff(np.concatenate(([False], line, [False])).astype(np.int8)))
        for start, end in zip(edges[0::2], edges[1::2], strict=True):
            path.addRect(x + int(start), row, int(end - start), 1)
    return path.simplified()


def bounding_rect(path: QPainterPath, margin: float) -> Rect:
    """Retângulo inteiro que envolve o caminho, com folga para a espessura."""
    box = path.boundingRect().adjusted(-margin, -margin, margin, margin)
    left = int(np.floor(box.left()))
    top = int(np.floor(box.top()))
    return left, top, int(np.ceil(box.right())) - left + 1, int(np.ceil(box.bottom())) - top + 1
