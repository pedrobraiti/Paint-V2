"""Ferramentas do editor: traduzem gestos do mouse em operações do núcleo."""

from .base import CanvasEvent, Tool, ToolContext
from .registry import DEFAULT_TOOL_KEY, TOOL_CLASSES, grouped_tool_classes
from .settings import ToolSettings

__all__ = [
    "CanvasEvent",
    "DEFAULT_TOOL_KEY",
    "TOOL_CLASSES",
    "Tool",
    "ToolContext",
    "ToolSettings",
    "grouped_tool_classes",
]
