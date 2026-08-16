import numpy as np
import pytest

from paintv2.core.adjustments import AdjustmentSettings
from paintv2.core.document import Document
from paintv2.core.fill import flood_fill
from paintv2.core.pixels import view


def test_blank_document_is_filled_with_the_requested_color():
    document = Document.blank(40, 30, (10, 20, 30, 255))
    assert (document.width, document.height) == (40, 30)
    assert tuple(document.pixels[0, 0]) == (10, 20, 30, 255)


def test_blank_document_buffer_is_contiguous_for_qt_sharing():
    document = Document.blank(17, 9)
    assert document.pixels.flags["C_CONTIGUOUS"]


def test_patch_undo_and_redo_restore_pixels():
    document = Document.blank(20, 20, (255, 255, 255, 255))
    rect = (5, 5, 4, 4)
    before = document.snapshot_region(rect)
    view(document.pixels, rect)[:] = (0, 0, 0, 255)
    document.commit_patch("Teste", rect, before)

    assert document.undo()
    assert tuple(document.pixels[6, 6]) == (255, 255, 255, 255)
    assert document.redo()
    assert tuple(document.pixels[6, 6]) == (0, 0, 0, 255)


def test_undo_without_history_returns_false():
    assert Document.blank(8, 8).undo() is False


def test_resize_changes_dimensions_and_is_undoable():
    document = Document.blank(40, 20)
    document.resize(20, 10)
    assert (document.width, document.height) == (20, 10)
    document.undo()
    assert (document.width, document.height) == (40, 20)


def test_crop_keeps_only_the_selected_region():
    document = Document.blank(20, 20, (255, 255, 255, 255))
    document.pixels[5:10, 5:10] = (255, 0, 0, 255)
    document.crop((5, 5, 5, 5))
    assert (document.width, document.height) == (5, 5)
    assert np.all(document.pixels[..., 0] == 255)
    assert np.all(document.pixels[..., 1] == 0)


def test_flip_horizontal_mirrors_content():
    document = Document.blank(4, 1, (0, 0, 0, 255))
    document.pixels[0, 0] = (255, 0, 0, 255)
    document.flip(horizontal=True)
    assert tuple(document.pixels[0, 3]) == (255, 0, 0, 255)


def test_rotate_ninety_degrees_swaps_dimensions():
    document = Document.blank(30, 10)
    document.rotate(90)
    assert (document.width, document.height) == (10, 30)


def test_expand_canvas_preserves_original_pixels():
    document = Document.blank(4, 4, (1, 2, 3, 255))
    document.expand_canvas(8, 8, (255, 255, 255, 255))
    assert tuple(document.pixels[0, 0]) == (1, 2, 3, 255)
    assert tuple(document.pixels[7, 7]) == (255, 255, 255, 255)


def test_stroke_buffers_follow_a_resize():
    document = Document.blank(30, 20)
    document.resize(10, 5)
    assert document.stroke_buffers.mask.shape == (5, 10)


def test_apply_adjustments_only_touches_the_given_rect():
    document = Document.blank(20, 20, (200, 100, 50, 255))
    settings = AdjustmentSettings(saturation=100.0)
    document.apply_adjustments(settings, rect=(0, 0, 10, 20))
    assert not np.array_equal(document.pixels[0, 0], document.pixels[0, 15])


def test_identity_adjustments_change_nothing():
    document = Document.blank(8, 8, (120, 130, 140, 255))
    original = document.pixels.copy()
    assert document.apply_adjustments(AdjustmentSettings()) is None
    assert np.array_equal(document.pixels, original)


@pytest.mark.parametrize("extension", [".png", ".jpg", ".bmp", ".webp"])
def test_save_and_reopen_roundtrip(tmp_path, extension):
    document = Document.blank(12, 8, (30, 60, 90, 255))
    destination = document.save(tmp_path / f"saida{extension}")

    assert destination.exists()
    assert document.is_dirty is False

    reopened = Document.open(destination)
    assert (reopened.width, reopened.height) == (12, 8)


def test_saving_jpeg_flattens_transparency_over_white(tmp_path):
    document = Document.blank(4, 4, (0, 0, 0, 0))
    reopened = Document.open(document.save(tmp_path / "transparente.jpg"))
    assert tuple(reopened.pixels[0, 0]) == (255, 255, 255, 255)


def test_thumbnail_fits_inside_the_requested_box():
    document = Document.blank(400, 200)
    thumbnail = document.thumbnail(64)
    assert max(thumbnail.shape[:2]) <= 64


def test_flood_fill_stops_at_a_barrier():
    document = Document.blank(20, 20, (255, 255, 255, 255))
    document.pixels[:, 10] = (0, 0, 0, 255)

    rect = flood_fill(document.pixels, 2, 2, np.array([255, 0, 0, 255], dtype=np.uint8))

    assert rect is not None
    assert tuple(document.pixels[2, 2]) == (255, 0, 0, 255)
    assert tuple(document.pixels[2, 15]) == (255, 255, 255, 255)


def test_flood_fill_with_tolerance_crosses_noise():
    document = Document.blank(20, 20, (255, 255, 255, 255))
    document.pixels[:, 10] = (250, 250, 250, 255)

    flood_fill(
        document.pixels, 2, 2, np.array([255, 0, 0, 255], dtype=np.uint8), tolerance=5.0
    )

    assert tuple(document.pixels[2, 15]) == (255, 0, 0, 255)


def test_global_flood_fill_ignores_connectivity():
    document = Document.blank(20, 20, (255, 255, 255, 255))
    document.pixels[:, 10] = (0, 0, 0, 255)

    flood_fill(
        document.pixels,
        2,
        2,
        np.array([255, 0, 0, 255], dtype=np.uint8),
        contiguous=False,
    )

    assert tuple(document.pixels[2, 15]) == (255, 0, 0, 255)


def test_flood_fill_outside_bounds_is_a_no_op():
    document = Document.blank(10, 10)
    assert flood_fill(document.pixels, 50, 50, np.array([0, 0, 0, 255], np.uint8)) is None
