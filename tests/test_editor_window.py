"""Testes da janela do editor e do HUB, sem abrir janela de verdade."""

from __future__ import annotations

import numpy as np
import pytest

from paintv2.core.document import Document
from paintv2.projects import ProjectLibrary
from paintv2.ui.hub_window import HubWindow
from paintv2.ui.main_window import MainWindow


@pytest.fixture
def library(tmp_path):
    return ProjectLibrary(root=tmp_path / "dados")


@pytest.fixture
def editor(qapp, library, textured_pixels):
    window = MainWindow(library)
    window.load_document(Document(textured_pixels()))
    return window


def test_editor_starts_with_a_document(editor):
    assert editor.document.width > 0
    assert editor.document.history.can_undo is False


def test_saving_registers_the_project_in_the_library(editor, library, tmp_path):
    destination = tmp_path / "obra.png"
    assert editor._write(destination) is True

    assert destination.is_file()
    assert [entry.name for entry in library.entries()] == ["obra.png"]
    assert editor.document.is_dirty is False


def test_title_marks_unsaved_changes(editor):
    editor.document.pixels[0, 0] = (1, 2, 3, 255)
    editor.document.is_dirty = True
    editor._refresh_title()
    assert "•" in editor.windowTitle()


def test_history_actions_follow_the_document(editor):
    assert editor._undo_action.isEnabled() is False

    rect = (2, 2, 6, 6)
    before = editor.document.snapshot_region(rect)
    editor.document.pixels[2:8, 2:8] = 0
    editor.document.commit_patch("Teste", rect, before)
    editor._on_document_modified()

    assert editor._undo_action.isEnabled() is True
    editor.undo()
    assert editor._redo_action.isEnabled() is True


def test_copy_and_paste_round_trip(editor):
    editor.select_all()
    editor.copy()
    editor.paste()
    editor._canvas.tool().commit_pending()
    assert editor.document.width > 0


def test_crop_to_selection_resizes_the_document(editor):
    editor.select_all()
    editor._canvas.selection.set_rect((10, 10, 30, 20))
    editor.crop_to_selection()
    assert (editor.document.width, editor.document.height) == (30, 20)


def test_crop_without_selection_is_a_no_op(editor):
    editor.deselect()
    size = (editor.document.width, editor.document.height)
    editor.crop_to_selection()
    assert (editor.document.width, editor.document.height) == size


def test_rotation_and_flip_go_through_the_document(editor):
    width, height = editor.document.width, editor.document.height
    editor.rotate(90)
    assert (editor.document.width, editor.document.height) == (height, width)

    mirrored = editor.document.pixels.copy()
    editor.flip(horizontal=True)
    assert np.array_equal(editor.document.pixels, np.flip(mirrored, axis=1))


def test_opening_a_missing_file_does_not_crash(editor, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)
    editor.open_file(tmp_path / "nao-existe.png")
    assert editor.document.width > 0


def test_adjustments_dialog_applies_on_accept(editor):
    from paintv2.ui.dialogs import AdjustmentsDialog

    dialog = AdjustmentsDialog(editor.document, editor._canvas, False, editor)
    before = editor.document.pixels.copy()
    dialog._sliders["saturation"].setValue(120)
    dialog.accept()

    assert not np.array_equal(before, editor.document.pixels)
    assert editor.document.history.can_undo


def test_adjustments_dialog_restores_pixels_on_cancel(editor):
    from paintv2.ui.dialogs import AdjustmentsDialog

    dialog = AdjustmentsDialog(editor.document, editor._canvas, False, editor)
    before = editor.document.pixels.copy()
    dialog._sliders["contrast"].setValue(80)
    dialog._render_preview()
    assert not np.array_equal(before, editor.document.pixels)

    dialog.reject()

    assert np.array_equal(before, editor.document.pixels)
    assert editor.document.history.can_undo is False


def test_adjustments_restricted_to_selection_spares_the_rest(editor):
    from paintv2.ui.dialogs import AdjustmentsDialog

    editor._canvas.selection.set_rect((0, 0, 40, editor.document.height))
    dialog = AdjustmentsDialog(editor.document, editor._canvas, True, editor)
    dialog._sliders["saturation"].setValue(150)
    outside_before = editor.document.pixels[:, 60:].copy()
    dialog.accept()

    assert np.array_equal(outside_before, editor.document.pixels[:, 60:])


def test_hub_lists_saved_projects(qapp, library, tmp_path):
    image = np.zeros((10, 10, 4), dtype=np.uint8)
    image[..., 3] = 255
    path = tmp_path / "recente.png"
    path.write_bytes(b"x")
    library.remember(path, image)

    hub = HubWindow(library)
    hub.refresh()

    assert hub._grid.count() == 1


def test_hub_hides_projects_whose_file_vanished(qapp, library, tmp_path):
    image = np.zeros((10, 10, 4), dtype=np.uint8)
    path = tmp_path / "sumiu.png"
    path.write_bytes(b"x")
    library.remember(path, image)
    path.unlink()

    hub = HubWindow(library)
    hub.refresh()

    assert hub._grid.count() == 0
    assert hub._empty_label.isVisible() or not hub.isVisible()


def test_hub_filter_narrows_the_list(qapp, library, tmp_path):
    image = np.zeros((8, 8, 4), dtype=np.uint8)
    for name in ("paisagem.png", "retrato.png"):
        path = tmp_path / name
        path.write_bytes(b"x")
        library.remember(path, image)

    hub = HubWindow(library)
    hub._search.setText("retrato")

    assert hub._grid.count() == 1
