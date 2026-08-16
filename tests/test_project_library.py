import json

import numpy as np
import pytest

from paintv2.projects.library import MAX_ENTRIES, ProjectLibrary


@pytest.fixture
def library(tmp_path):
    return ProjectLibrary(root=tmp_path / "dados")


def make_image(width=20, height=10):
    pixels = np.zeros((height, width, 4), dtype=np.uint8)
    pixels[..., 0] = 200
    pixels[..., 3] = 255
    return pixels


def make_file(tmp_path, name="projeto.png"):
    path = tmp_path / name
    path.write_bytes(b"conteudo")
    return path


def test_new_library_is_empty(library):
    assert library.entries() == []


def test_remember_stores_dimensions_and_thumbnail(tmp_path, library):
    path = make_file(tmp_path)
    entry = library.remember(path, make_image(40, 25))

    assert entry.width == 40 and entry.height == 25
    assert entry.thumbnail_path is not None and entry.thumbnail_path.is_file()
    assert [item.name for item in library.entries()] == ["projeto.png"]


def test_remember_twice_keeps_a_single_entry(tmp_path, library):
    path = make_file(tmp_path)
    library.remember(path, make_image())
    library.remember(path, make_image())
    assert len(library.entries()) == 1


def test_entries_are_sorted_from_newest_to_oldest(tmp_path, library):
    first = make_file(tmp_path, "antigo.png")
    second = make_file(tmp_path, "novo.png")
    library.remember(first, make_image())
    library.remember(second, make_image())

    # A ordenação usa o carimbo gravado; empatar no mesmo segundo é possível,
    # então o teste força a diferença mexendo no campo.
    library._entries[0].opened_at = "2020-01-01T00:00:00+00:00"
    assert library.entries()[0].name == "novo.png"


def test_library_survives_a_restart(tmp_path):
    root = tmp_path / "dados"
    path = make_file(tmp_path)
    ProjectLibrary(root=root).remember(path, make_image())

    assert [entry.name for entry in ProjectLibrary(root=root).entries()] == ["projeto.png"]


def test_missing_files_are_hidden_and_prunable(tmp_path, library):
    path = make_file(tmp_path)
    library.remember(path, make_image())
    path.unlink()

    assert library.entries() == []
    assert library.prune_missing() == 1
    assert library.entries(include_missing=True) == []


def test_forget_removes_entry_and_thumbnail(tmp_path, library):
    path = make_file(tmp_path)
    entry = library.remember(path, make_image())
    thumbnail = entry.thumbnail_path

    library.forget(path)

    assert library.entries(include_missing=True) == []
    assert thumbnail is not None and not thumbnail.exists()


def test_forget_does_not_delete_the_users_file(tmp_path, library):
    path = make_file(tmp_path)
    library.remember(path, make_image())
    library.forget(path)
    assert path.exists()


def test_corrupted_index_is_ignored_instead_of_crashing(tmp_path):
    root = tmp_path / "dados"
    root.mkdir(parents=True)
    (root / "library.json").write_text("{isto nao e json", encoding="utf-8")

    assert ProjectLibrary(root=root).entries() == []


def test_index_is_valid_json(tmp_path, library):
    library.remember(make_file(tmp_path), make_image())
    payload = json.loads((tmp_path / "dados" / "library.json").read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert len(payload["projects"]) == 1


def test_library_is_capped(tmp_path, library):
    for index in range(MAX_ENTRIES + 5):
        library.remember(make_file(tmp_path, f"arquivo{index}.png"), make_image())
    assert len(library.entries()) == MAX_ENTRIES
