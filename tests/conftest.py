"""Configuração comum dos testes.

O Qt é forçado para a plataforma ``offscreen`` **antes** de qualquer import dele:
os testes de interface precisam rodar sem abrir janela, tanto na máquina do
desenvolvedor quanto em integração contínua.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def textured_pixels():
    """Padrão com variação local — efeitos como blend e desfoque precisam dela."""

    def build(width: int = 120, height: int = 90) -> np.ndarray:
        rows, columns = np.mgrid[0:height, 0:width]
        pixels = np.empty((height, width, 4), dtype=np.uint8)
        pixels[..., 0] = (columns * 7) % 256
        pixels[..., 1] = (rows * 5 + 40) % 256
        pixels[..., 2] = ((rows + columns) * 3) % 256
        pixels[..., 3] = 255
        return pixels

    return build
