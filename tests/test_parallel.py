"""Testes da divisão do carimbo em faixas."""

import numpy as np
import pytest

from paintv2.core import brush_modes
from paintv2.core.brush_tips import MAX_SIZE, get_tip
from paintv2.core.parallel import Band, run_in_parallel, split_into_bands
from paintv2.core.stroke import StrokeBuffers, StrokeEngine


def test_small_rect_is_a_single_band():
    bands = list(split_into_bands((0, 0, 40, 40)))
    assert len(bands) == 1
    assert bands[0].rect == bands[0].padded == (0, 0, 40, 40)


def test_bands_cover_the_rect_exactly_once():
    rect = (10, 5, 900, 900)
    bands = list(split_into_bands(rect))
    assert len(bands) > 1

    covered = np.zeros(rect[3], dtype=int)
    for band in bands:
        assert band.rect[0] == rect[0] and band.rect[2] == rect[2]
        covered[band.rect[1] - rect[1] : band.rect[1] - rect[1] + band.rect[3]] += 1
    assert np.all(covered == 1)


def test_bands_have_similar_heights():
    bands = list(split_into_bands((0, 0, 500, 1000)))
    heights = [band.rect[3] for band in bands]
    assert max(heights) - min(heights) <= 1


def test_halo_expands_only_the_area_that_is_read():
    bands = list(split_into_bands((0, 0, 400, 2000), halo=8))
    middle = bands[len(bands) // 2]
    assert middle.padded[1] < middle.rect[1]
    assert middle.padded[3] > middle.rect[3]


def test_halo_is_clipped_at_the_edges():
    bands = list(split_into_bands((0, 0, 400, 2000), halo=8))
    assert bands[0].padded[1] == 0
    assert bands[-1].padded[1] + bands[-1].padded[3] == 2000


def test_crop_removes_the_halo_rows():
    band = Band(rect=(0, 10, 4, 6), padded=(0, 7, 4, 12))
    array = np.arange(12 * 4).reshape(12, 4)
    cropped = band.crop(array)
    assert cropped.shape == (6, 4)
    assert np.array_equal(cropped, array[3:9])


def test_rows_within_locates_the_band_in_the_parent():
    band = Band(rect=(0, 30, 5, 10), padded=(0, 30, 5, 10))
    assert band.rows_within((0, 20, 5, 100)) == slice(10, 20)


def test_empty_rect_produces_no_bands():
    assert list(split_into_bands((0, 0, 0, 10))) == []


def test_run_in_parallel_propagates_failures():
    def explode(_band):
        raise ValueError("falha na faixa")

    with pytest.raises(ValueError, match="falha na faixa"):
        run_in_parallel(explode, split_into_bands((0, 0, 400, 2000)))


# --------------------------------------------------------- integração no traço


def stroke_with(pixels, mode, size, tip="brush"):
    engine = StrokeEngine(
        pixels, get_tip(tip), mode, size, StrokeBuffers(*pixels.shape[:2]), seed=3
    )
    engine.begin(60, pixels.shape[0] / 2)
    engine.move(pixels.shape[1] - 60, pixels.shape[0] / 2)
    return engine.end()


def textured(width=900, height=700):
    rows, columns = np.mgrid[0:height, 0:width]
    pixels = np.empty((height, width, 4), dtype=np.uint8)
    pixels[..., 0] = (columns * 3) % 256
    pixels[..., 1] = (rows * 5) % 256
    pixels[..., 2] = ((rows + columns) * 2) % 256
    pixels[..., 3] = 255
    return pixels


@pytest.mark.parametrize(
    "factory",
    [
        lambda: brush_modes.SaturationMode(0.7),
        lambda: brush_modes.BlurMode(0.5, 400.0),
        lambda: brush_modes.SharpenMode(0.6),
        lambda: brush_modes.ContrastMode(0.5),
        lambda: brush_modes.LevelsMode(0.8),
    ],
    ids=["saturação", "desfoque", "nitidez", "contraste", "faixa tonal"],
)
def test_banded_stroke_leaves_no_seams(factory):
    """Um traço largo o bastante para virar várias faixas não pode listrar.

    Se a borda de segurança falhasse, apareceria uma descontinuidade brusca em
    cada divisão — detectável comparando linhas vizinhas no meio do traço.
    """
    pixels = textured()
    stroke_with(pixels, factory(), 400.0)

    column = pixels[:, pixels.shape[1] // 2, :3].astype(np.int16)
    row_deltas = np.abs(np.diff(column, axis=0)).max(axis=1)

    original = textured()[:, pixels.shape[1] // 2, :3].astype(np.int16)
    original_deltas = np.abs(np.diff(original, axis=0)).max(axis=1)

    # Nenhuma transição criada pelo traço pode ser mais brusca que as que a
    # própria imagem já tinha.
    assert row_deltas.max() <= original_deltas.max() + 2


def test_huge_brush_stays_within_memory_and_paints():
    """Um pincel maior que a imagem tem de funcionar sem estourar a memória."""
    pixels = textured(700, 500)
    before = pixels.copy()
    stroke_with(pixels, brush_modes.SaturationMode(0.9), 2000.0)
    assert not np.array_equal(before, pixels)


def test_brush_size_is_capped_at_the_engine_limit():
    pixels = textured(200, 160)
    before = pixels.copy()
    stroke_with(pixels, brush_modes.SaturationMode(0.9), MAX_SIZE * 4)
    assert not np.array_equal(before, pixels)


def test_blend_across_bands_keeps_dragging_color():
    """O acumulador do blend precisa sobreviver à divisão em faixas."""
    pixels = np.empty((600, 800, 4), dtype=np.uint8)
    pixels[:] = (255, 255, 255, 255)
    pixels[:, :400] = (0, 0, 0, 255)

    engine = StrokeEngine(
        pixels,
        get_tip("brush"),
        brush_modes.BlendSmudgeMode(0.9),
        360.0,
        StrokeBuffers(600, 800),
        seed=5,
    )
    engine.begin(380, 300)
    for x in range(390, 520, 6):
        engine.move(x, 300)
    engine.end()

    smeared = pixels[280:320, 470, 0]
    assert np.all(smeared > 0) and np.all(smeared < 255)
    # E o arrasto tem de ser parecido em toda a altura do pincel, não cortado
    # por faixa.
    column = pixels[200:400, 470, 0].astype(np.int16)
    assert np.abs(np.diff(column)).max() < 60
