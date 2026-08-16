import numpy as np

from paintv2.core.brush_modes import PaintMode
from paintv2.core.brush_tips import get_tip
from paintv2.core.document import Document
from paintv2.core.fill import flood_fill
from paintv2.core.selection import Selection
from paintv2.core.stroke import StrokeEngine


def make_selection(width=40, height=40) -> Selection:
    return Selection(width, height)


def test_new_selection_is_inactive():
    selection = make_selection()
    assert selection.is_active is False
    assert selection.bounds is None
    assert selection.clip_weights() is None


def test_rect_selection_reports_bounds():
    selection = make_selection()
    selection.set_rect((5, 8, 10, 12))
    assert selection.bounds == (5, 8, 10, 12)
    assert selection.contains(6, 9)
    assert not selection.contains(4, 9)


def test_rect_selection_is_clipped_to_the_canvas():
    selection = make_selection(20, 20)
    selection.set_rect((-10, -10, 15, 15))
    assert selection.bounds == (0, 0, 5, 5)


def test_selection_entirely_outside_the_canvas_clears():
    selection = make_selection(20, 20)
    selection.set_rect((100, 100, 10, 10))
    assert selection.is_active is False


def test_select_all_covers_everything():
    selection = make_selection(30, 20)
    selection.select_all()
    assert selection.bounds == (0, 0, 30, 20)


def test_invert_swaps_inside_and_outside():
    selection = make_selection(10, 10)
    selection.set_rect((0, 0, 4, 10))
    selection.invert()
    assert selection.contains(5, 5)
    assert not selection.contains(1, 5)


def test_mask_selection_derives_tight_bounds():
    selection = make_selection(20, 20)
    mask = np.zeros((20, 20), dtype=bool)
    mask[4:9, 3:11] = True
    selection.set_mask(mask)
    assert selection.bounds == (3, 4, 8, 5)


def test_empty_mask_clears_the_selection():
    selection = make_selection()
    selection.set_mask(np.zeros((40, 40), dtype=bool))
    assert selection.is_active is False


def test_stroke_is_confined_to_the_selection():
    document = Document.blank(60, 60, (255, 255, 255, 255))
    selection = Selection(60, 60)
    selection.set_rect((0, 0, 30, 60))

    engine = StrokeEngine(
        document.pixels,
        get_tip("brush"),
        PaintMode(np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32), 1.0),
        14.0,
        document.stroke_buffers,
        clip_mask=selection.clip_weights(),
    )
    engine.begin(5, 30)
    engine.move(55, 30)
    engine.end()

    assert tuple(document.pixels[30, 10]) == (255, 0, 0, 255)
    assert tuple(document.pixels[30, 50]) == (255, 255, 255, 255)


def test_flood_fill_is_confined_to_the_selection():
    document = Document.blank(40, 40, (255, 255, 255, 255))
    selection = Selection(40, 40)
    selection.set_rect((0, 0, 20, 40))

    flood_fill(
        document.pixels,
        5,
        5,
        np.array([0, 0, 255, 255], dtype=np.uint8),
        clip=selection.mask,
    )

    assert tuple(document.pixels[5, 5]) == (0, 0, 255, 255)
    assert tuple(document.pixels[5, 30]) == (255, 255, 255, 255)


def test_resizing_the_canvas_drops_the_selection():
    selection = make_selection()
    selection.select_all()
    selection.resize_canvas(10, 10)
    assert selection.is_active is False
