"""Histórico de desfazer/refazer.

Guardar a imagem inteira a cada passo é inviável numa foto grande, então a
entrada padrão é um *patch*: apenas o retângulo alterado, antes e depois. Só
operações que mudam as dimensões do documento (redimensionar, girar, recortar)
guardam o buffer completo.
"""

from __future__ import annotations

from collections import deque
from typing import Protocol

import numpy as np

from .pixels import Rect, view

DEFAULT_MEMORY_LIMIT = 512 * 1024 * 1024


class HistoryTarget(Protocol):
    """O que o histórico precisa saber sobre o documento que ele edita."""

    pixels: np.ndarray

    def replace_pixels(self, pixels: np.ndarray) -> None: ...


class HistoryEntry(Protocol):
    label: str

    @property
    def nbytes(self) -> int: ...

    def undo(self, target: HistoryTarget) -> None: ...

    def redo(self, target: HistoryTarget) -> None: ...


class PatchEntry:
    """Alteração restrita a um retângulo, com os pixels de antes e de depois."""

    def __init__(self, label: str, rect: Rect, before: np.ndarray, after: np.ndarray) -> None:
        self.label = label
        self._rect = rect
        self._before = before
        self._after = after

    @property
    def nbytes(self) -> int:
        return self._before.nbytes + self._after.nbytes

    def undo(self, target: HistoryTarget) -> None:
        view(target.pixels, self._rect)[:] = self._before

    def redo(self, target: HistoryTarget) -> None:
        view(target.pixels, self._rect)[:] = self._after


class ReplaceEntry:
    """Substituição integral do buffer — muda dimensões do documento."""

    def __init__(self, label: str, before: np.ndarray, after: np.ndarray) -> None:
        self.label = label
        self._before = before
        self._after = after

    @property
    def nbytes(self) -> int:
        return self._before.nbytes + self._after.nbytes

    def undo(self, target: HistoryTarget) -> None:
        target.replace_pixels(self._before.copy())

    def redo(self, target: HistoryTarget) -> None:
        target.replace_pixels(self._after.copy())


class History:
    """Pilha de desfazer/refazer com teto de memória."""

    def __init__(self, memory_limit: int = DEFAULT_MEMORY_LIMIT) -> None:
        self._memory_limit = memory_limit
        self._undo_stack: deque[HistoryEntry] = deque()
        self._redo_stack: list[HistoryEntry] = []
        self._used_bytes = 0

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def undo_label(self) -> str | None:
        return self._undo_stack[-1].label if self._undo_stack else None

    @property
    def redo_label(self) -> str | None:
        return self._redo_stack[-1].label if self._redo_stack else None

    def push(self, entry: HistoryEntry) -> None:
        """Registra uma alteração já aplicada, invalidando o refazer pendente."""
        self._undo_stack.append(entry)
        self._used_bytes += entry.nbytes
        self._redo_stack.clear()
        self._enforce_limit()

    def undo(self, target: HistoryTarget) -> HistoryEntry | None:
        if not self._undo_stack:
            return None
        entry = self._undo_stack.pop()
        self._used_bytes -= entry.nbytes
        entry.undo(target)
        self._redo_stack.append(entry)
        return entry

    def redo(self, target: HistoryTarget) -> HistoryEntry | None:
        if not self._redo_stack:
            return None
        entry = self._redo_stack.pop()
        entry.redo(target)
        self._undo_stack.append(entry)
        self._used_bytes += entry.nbytes
        return entry

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._used_bytes = 0

    def _enforce_limit(self) -> None:
        while self._used_bytes > self._memory_limit and len(self._undo_stack) > 1:
            dropped = self._undo_stack.popleft()
            self._used_bytes -= dropped.nbytes


def capture_patch(
    label: str, pixels: np.ndarray, rect: Rect, before: np.ndarray
) -> PatchEntry:
    """Monta o patch a partir do estado anterior já guardado e do buffer atual."""
    return PatchEntry(label, rect, before, view(pixels, rect).copy())
