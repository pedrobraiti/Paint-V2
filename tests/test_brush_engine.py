import numpy as np
import pytest

from paintv2.core import brush_modes, brush_tips
from paintv2.core.brush_tips import StampRequest, TIPS
from paintv2.core.stroke import StrokeBuffers, StrokeEngine


def make_canvas(color=(128, 128, 128, 255), size=64) -> np.ndarray:
    canvas = np.empty((size, size, 4), dtype=np.uint8)
    canvas[:] = np.asarray(color, dtype=np.uint8)
    return canvas


def run_stroke(canvas, tip, mode, size=12.0, path=((10, 32), (50, 32))):
    engine = StrokeEngine(
        canvas, tip, mode, size, StrokeBuffers(*canvas.shape[:2]), seed=7
    )
    engine.begin(*path[0])
    for point in path[1:]:
        engine.move(*point)
    return engine.end()


# --------------------------------------------------------------------- pontas


@pytest.mark.parametrize("tip", TIPS, ids=lambda tip: tip.key)
def test_every_tip_renders_a_valid_mask(tip):
    mask = brush_tips.render_stamp(
        tip, StampRequest(size=20.0, rng=np.random.default_rng(3))
    )
    assert mask.dtype == np.float32
    assert mask.shape == (mask.shape[0], mask.shape[0])
    assert mask.min() >= 0.0 and mask.max() <= 1.0
    assert mask.any(), "a ponta não marcou nenhum pixel"


@pytest.mark.parametrize("tip", TIPS, ids=lambda tip: tip.key)
def test_stamp_extent_matches_rendered_mask(tip):
    size = 17.0
    mask = brush_tips.render_stamp(
        tip, StampRequest(size=size, rng=np.random.default_rng(1))
    )
    assert mask.shape[0] == brush_tips.stamp_extent(tip, size)


def test_soft_tip_fades_towards_the_edge():
    tip = brush_tips.get_tip("soft")
    mask = brush_tips.render_stamp(tip, StampRequest(size=32.0))
    center = mask.shape[0] // 2
    assert mask[center, center] > mask[center, center + 12] > 0.0


def test_spray_is_sparse_and_random():
    tip = brush_tips.get_tip("airbrush")
    first = brush_tips.render_stamp(
        tip, StampRequest(size=40.0, rng=np.random.default_rng(1))
    )
    second = brush_tips.render_stamp(
        tip, StampRequest(size=40.0, rng=np.random.default_rng(2))
    )
    assert not np.array_equal(first, second)
    assert 0.0 < first.mean() < 0.6, "spray deveria deixar buracos, não cobrir tudo"


# ---------------------------------------------------------------------- modos


def test_paint_mode_applies_the_selected_color():
    canvas = make_canvas()
    color = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
    run_stroke(canvas, brush_tips.get_tip("brush"), brush_modes.PaintMode(color, 1.0))
    assert tuple(canvas[32, 30][:3]) == (255, 0, 0)


def test_erase_mode_clears_alpha():
    canvas = make_canvas()
    run_stroke(canvas, brush_tips.get_tip("brush"), brush_modes.EraseMode(1.0, None))
    assert canvas[32, 30, 3] == 0


@pytest.mark.parametrize("tip", TIPS, ids=lambda tip: tip.key)
def test_saturation_works_with_every_tip(tip):
    canvas = make_canvas(color=(180, 90, 60, 255))
    original = canvas.copy()
    run_stroke(canvas, tip, brush_modes.SaturationMode(1.0), size=20.0)
    assert not np.array_equal(canvas, original), f"{tip.key} não alterou nada"
    assert canvas[32, 30, 0] >= original[32, 30, 0]


def test_saturation_stroke_is_independent_of_sample_density():
    """Passar devagar e passar rápido no mesmo caminho tem de dar o mesmo resultado."""
    tip = brush_tips.get_tip("brush")

    sparse = make_canvas(color=(200, 100, 50, 255))
    run_stroke(sparse, tip, brush_modes.SaturationMode(0.6), path=((10, 32), (50, 32)))

    dense = make_canvas(color=(200, 100, 50, 255))
    detailed = tuple((x, 32) for x in range(10, 51))
    run_stroke(dense, tip, brush_modes.SaturationMode(0.6), path=detailed)

    assert np.array_equal(sparse, dense)


def test_desaturation_moves_towards_gray():
    canvas = make_canvas(color=(200, 60, 60, 255))
    run_stroke(canvas, brush_tips.get_tip("brush"), brush_modes.SaturationMode(-1.0))
    red, green, blue = canvas[32, 30][:3].astype(int)
    assert abs(red - green) < 10 and abs(green - blue) < 10


def test_blend_mode_drags_color_across_an_edge():
    canvas = make_canvas(color=(255, 255, 255, 255))
    canvas[:, :32] = (0, 0, 0, 255)
    run_stroke(
        canvas,
        brush_tips.get_tip("brush"),
        brush_modes.BlendSmudgeMode(0.9),
        size=16.0,
        path=tuple((x, 32) for x in range(24, 45)),
    )
    smeared = canvas[32, 40, 0]
    assert 0 < smeared < 255, "o blend deveria deixar um degradê, não uma borda dura"


def test_blur_mode_reduces_local_contrast():
    canvas = make_canvas(color=(255, 255, 255, 255))
    canvas[:, ::2] = (0, 0, 0, 255)
    before = canvas[28:36, 28:36, 0].astype(np.float32).std()
    run_stroke(canvas, brush_tips.get_tip("brush"), brush_modes.BlurMode(1.0, 24.0), size=24.0)
    after = canvas[28:36, 28:36, 0].astype(np.float32).std()
    assert after < before


def test_dodge_lightens_and_burn_darkens():
    lightened = make_canvas(color=(100, 100, 100, 255))
    run_stroke(lightened, brush_tips.get_tip("brush"), brush_modes.DodgeMode(0.8))
    assert lightened[32, 30, 0] > 100

    darkened = make_canvas(color=(100, 100, 100, 255))
    run_stroke(darkened, brush_tips.get_tip("brush"), brush_modes.BurnMode(0.8))
    assert darkened[32, 30, 0] < 100


def test_stroke_reports_dirty_rect_inside_canvas():
    canvas = make_canvas()
    dirty = run_stroke(canvas, brush_tips.get_tip("brush"), brush_modes.SaturationMode(0.5))
    x, y, width, height = dirty
    assert x >= 0 and y >= 0
    assert x + width <= canvas.shape[1]
    assert y + height <= canvas.shape[0]


def test_stroke_outside_canvas_is_ignored():
    canvas = make_canvas()
    original = canvas.copy()
    color = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)
    run_stroke(
        canvas,
        brush_tips.get_tip("brush"),
        brush_modes.PaintMode(color, 1.0),
        path=((-500, -500), (-400, -500)),
    )
    assert np.array_equal(canvas, original)


def test_stroke_buffer_is_cleared_for_reuse():
    canvas = make_canvas()
    buffers = StrokeBuffers(*canvas.shape[:2])
    color = np.array([1.0, 0.0, 0.0, 1.0], dtype=np.float32)

    engine = StrokeEngine(canvas, brush_tips.get_tip("brush"), brush_modes.PaintMode(color, 1.0), 12.0, buffers)
    engine.begin(20, 20)
    engine.move(40, 20)
    engine.end()

    assert not buffers.mask.any(), "a máscara precisa voltar zerada para o próximo traço"
