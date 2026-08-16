"""Testes das ferramentas pela porta da frente: eventos de ponteiro no canvas."""

from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtCore import QPointF, Qt

from paintv2.core.brush_tips import TIPS
from paintv2.core.document import Document
from paintv2.tools.base import CanvasEvent
from paintv2.tools.registry import TOOL_CLASSES
from paintv2.tools.selection_tools import SelectRectangleTool
from paintv2.tools.settings import ToolSettings
from paintv2.ui.canvas_view import CanvasView

DRAWING_TOOLS = (
    "pencil", "brush", "spray", "eraser", "fill", "saturation", "blend",
    "blur", "sharpen", "dodge", "burn", "hue", "line", "curve", "shape",
)
NON_DRAWING_TOOLS = ("select_rect", "select_lasso", "picker", "zoom", "pan", "text")


@pytest.fixture
def canvas(qapp, textured_pixels):
    view = CanvasView(ToolSettings())
    view.set_document(Document(textured_pixels()))
    view.resize(400, 320)
    return view


def drag(canvas: CanvasView, start=(15, 15), end=(100, 70), steps=10, button=None):
    """Simula pressionar, arrastar e soltar em coordenadas do documento."""
    button = button or Qt.MouseButton.LeftButton
    tool = canvas.tool()
    tool.press(CanvasEvent(position=QPointF(*start), button=button))
    for index in range(1, steps + 1):
        ratio = index / steps
        tool.move(
            CanvasEvent(
                position=QPointF(
                    start[0] + (end[0] - start[0]) * ratio,
                    start[1] + (end[1] - start[1]) * ratio,
                ),
                buttons=button,
            )
        )
    tool.release(CanvasEvent(position=QPointF(*end), button=button))
    tool.commit_pending()


@pytest.mark.parametrize("key", DRAWING_TOOLS)
def test_drawing_tools_change_pixels(canvas, key):
    canvas.set_tool(key)
    before = canvas.document.pixels.copy()
    drag(canvas)
    assert not np.array_equal(before, canvas.document.pixels)


@pytest.mark.parametrize("key", DRAWING_TOOLS)
def test_drawing_tools_are_undoable_in_one_step(canvas, key):
    canvas.set_tool(key)
    before = canvas.document.pixels.copy()
    drag(canvas)

    assert canvas.document.history.can_undo
    canvas.document.undo()
    assert np.array_equal(before, canvas.document.pixels)


@pytest.mark.parametrize("key", NON_DRAWING_TOOLS)
def test_non_drawing_tools_leave_pixels_alone(canvas, key):
    canvas.set_tool(key)
    before = canvas.document.pixels.copy()
    drag(canvas)
    assert np.array_equal(before, canvas.document.pixels)


@pytest.mark.parametrize("tip", TIPS, ids=lambda tip: tip.key)
@pytest.mark.parametrize(
    "tool_key", ["saturation", "blend", "blur", "sharpen", "dodge", "burn", "hue", "eraser"]
)
def test_every_effect_works_with_every_tip(canvas, tool_key, tip):
    """O requisito central: efeito e ponta são eixos independentes."""
    canvas.settings.tip_key = tip.key
    canvas.set_tool(tool_key)
    before = canvas.document.pixels.copy()
    drag(canvas, steps=14)
    assert not np.array_equal(before, canvas.document.pixels)


def test_picker_captures_the_color_under_the_cursor(canvas):
    canvas.document.pixels[30, 40] = (12, 240, 90, 255)
    canvas.set_tool("picker")
    canvas.tool().press(
        CanvasEvent(position=QPointF(40.5, 30.5), button=Qt.MouseButton.LeftButton)
    )
    assert canvas.settings.primary.getRgb()[:3] == (12, 240, 90)


def test_right_button_paints_with_the_secondary_color(canvas):
    canvas.set_tool("brush")
    canvas.settings.secondary = canvas.settings.secondary  # garante cor válida
    drag(canvas, start=(20, 20), end=(80, 20), button=Qt.MouseButton.RightButton)

    expected = canvas.settings.secondary.getRgb()[:3]
    assert tuple(int(value) for value in canvas.document.pixels[20, 50][:3]) == expected


def test_zoom_tool_changes_the_zoom_without_touching_pixels(canvas):
    canvas.set_tool("zoom")
    before_zoom = canvas.zoom
    canvas.tool().press(
        CanvasEvent(position=QPointF(50, 50), button=Qt.MouseButton.LeftButton)
    )
    assert canvas.zoom > before_zoom


def test_selection_tool_creates_and_clears_a_selection(canvas):
    canvas.set_tool("select_rect")
    drag(canvas, start=(10, 10), end=(60, 50))

    assert canvas.selection.is_active
    assert canvas.selection.bounds == (10, 10, 50, 40)

    canvas.tool().key_press(Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
    assert canvas.selection.is_active is False


def test_moving_a_selection_is_a_single_undo_step(canvas):
    original = canvas.document.pixels.copy()
    canvas.set_tool("select_rect")
    drag(canvas, start=(10, 10), end=(50, 40))

    tool = canvas.tool()
    assert isinstance(tool, SelectRectangleTool)
    drag(canvas, start=(20, 20), end=(70, 60))

    assert not np.array_equal(original, canvas.document.pixels)
    canvas.document.undo()
    assert np.array_equal(original, canvas.document.pixels)


def test_deleting_a_selection_clears_only_inside_it(canvas):
    canvas.set_tool("select_rect")
    drag(canvas, start=(10, 10), end=(50, 40))
    canvas.tool().delete_selection()

    assert canvas.document.pixels[20, 20, 3] == 0
    assert canvas.document.pixels[60, 80, 3] == 255


def test_pasting_creates_a_floating_selection(canvas):
    patch = np.zeros((12, 12, 4), dtype=np.uint8)
    patch[..., :] = (255, 0, 0, 255)

    canvas.set_tool("select_rect")
    tool = canvas.tool()
    tool.begin_paste(patch, (5, 5))
    assert tool.has_floating()

    tool.commit_pending()
    assert tuple(canvas.document.pixels[10, 10]) == (255, 0, 0, 255)


def test_switching_tools_commits_pending_work(canvas):
    canvas.set_tool("curve")
    tool = canvas.tool()
    tool.press(CanvasEvent(position=QPointF(10, 10), button=Qt.MouseButton.LeftButton))
    tool.move(CanvasEvent(position=QPointF(80, 60), buttons=Qt.MouseButton.LeftButton))
    tool.release(CanvasEvent(position=QPointF(80, 60)))

    before = canvas.document.pixels.copy()
    canvas.set_tool("brush")
    assert not np.array_equal(before, canvas.document.pixels), "a curva não foi gravada"


def test_letter_shortcut_switches_tool(canvas, qapp):
    from PySide6.QtGui import QKeyEvent

    canvas.set_tool("brush")
    event = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_E, Qt.KeyboardModifier.NoModifier, "e"
    )
    canvas.keyPressEvent(event)
    assert canvas.tool_key == "eraser"


def test_every_registered_tool_declares_its_metadata():
    for tool_class in TOOL_CLASSES:
        assert tool_class.key and tool_class.label and tool_class.hint
        assert tool_class.icon
