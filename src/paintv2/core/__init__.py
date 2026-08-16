"""Núcleo de imagem do Paint-V2 — NumPy puro, sem dependência de Qt."""

from .adjustments import AdjustmentSettings, apply_adjustments
from .document import Document
from .fill import flood_fill
from .history import History
from .stroke import StrokeBuffers, StrokeEngine

__all__ = [
    "AdjustmentSettings",
    "Document",
    "History",
    "StrokeBuffers",
    "StrokeEngine",
    "apply_adjustments",
    "flood_fill",
]
