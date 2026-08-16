"""Catálogo de ferramentas, na ordem em que aparecem na barra lateral."""

from __future__ import annotations

from .base import Tool
from .basic_tools import FillTool, PanTool, PickerTool, ZoomTool
from .brush_tools import (
    BlendBrushTool,
    BlurBrushTool,
    BrushTool,
    BurnBrushTool,
    DodgeBrushTool,
    EraserTool,
    HueBrushTool,
    PencilTool,
    SaturationBrushTool,
    SharpenBrushTool,
    SprayTool,
)
from .selection_tools import SelectLassoTool, SelectRectangleTool, SelectionTool
from .shape_tools import CurveTool, LineTool, ShapeTool
from .text_tool import TextTool

GROUP_ORDER = ("seleção", "desenho", "efeitos", "formas", "navegação")

GROUP_LABELS = {
    "seleção": "Seleção",
    "desenho": "Desenho",
    "efeitos": "Pincéis de efeito",
    "formas": "Formas",
    "navegação": "Navegação",
}

TOOL_CLASSES: tuple[type[Tool], ...] = (
    SelectRectangleTool,
    SelectLassoTool,
    PencilTool,
    BrushTool,
    SprayTool,
    EraserTool,
    FillTool,
    PickerTool,
    TextTool,
    SaturationBrushTool,
    BlendBrushTool,
    BlurBrushTool,
    SharpenBrushTool,
    DodgeBrushTool,
    BurnBrushTool,
    HueBrushTool,
    LineTool,
    CurveTool,
    ShapeTool,
    ZoomTool,
    PanTool,
)

DEFAULT_TOOL_KEY = BrushTool.key


def grouped_tool_classes() -> list[tuple[str, list[type[Tool]]]]:
    """Ferramentas agrupadas e rotuladas para montar a barra lateral."""
    groups: dict[str, list[type[Tool]]] = {name: [] for name in GROUP_ORDER}
    for tool_class in TOOL_CLASSES:
        groups.setdefault(tool_class.group, []).append(tool_class)
    return [
        (GROUP_LABELS.get(name, name.title()), members)
        for name, members in groups.items()
        if members
    ]


__all__ = [
    "DEFAULT_TOOL_KEY",
    "GROUP_LABELS",
    "TOOL_CLASSES",
    "SelectionTool",
    "grouped_tool_classes",
]
