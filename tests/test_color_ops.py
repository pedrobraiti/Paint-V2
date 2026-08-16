import numpy as np
import pytest

from paintv2.core import color_ops


def make_rgb(*colors: tuple[float, float, float]) -> np.ndarray:
    return np.array(colors, dtype=np.float32)


def test_saturation_zero_collapses_to_luminance():
    rgb = make_rgb((0.8, 0.2, 0.4))
    result = color_ops.adjust_saturation(rgb, 0.0)
    assert result[0, 0] == pytest.approx(result[0, 1])
    assert result[0, 1] == pytest.approx(result[0, 2])


def test_saturation_neutral_factor_is_a_no_op():
    rgb = make_rgb((0.3, 0.6, 0.9))
    assert np.allclose(color_ops.adjust_saturation(rgb, 1.0), rgb)


def test_saturation_preserves_luminance():
    rgb = make_rgb((0.7, 0.35, 0.1))
    boosted = color_ops.adjust_saturation(rgb, 1.8)
    assert color_ops.luminance(boosted)[0] == pytest.approx(
        color_ops.luminance(rgb)[0], abs=1e-5
    )


def test_saturation_leaves_gray_untouched():
    gray = make_rgb((0.5, 0.5, 0.5))
    assert np.allclose(color_ops.adjust_saturation(gray, 3.0), gray)


def test_vibrance_boosts_dull_colors_more_than_vivid_ones():
    dull = make_rgb((0.5, 0.45, 0.5))
    vivid = make_rgb((1.0, 0.0, 0.0))

    dull_gain = np.abs(color_ops.adjust_vibrance(dull, 1.0) - dull).max()
    vivid_gain = np.abs(color_ops.adjust_vibrance(vivid, 1.0) - vivid).max()

    assert dull_gain > vivid_gain


def test_hue_rotation_of_360_degrees_returns_original():
    rgb = make_rgb((0.9, 0.3, 0.1))
    assert np.allclose(color_ops.adjust_hue(rgb, 360.0), rgb, atol=1e-5)


def test_hue_rotation_preserves_luminance():
    rgb = make_rgb((0.9, 0.3, 0.1))
    rotated = color_ops.adjust_hue(rgb, 120.0)
    assert color_ops.luminance(rotated)[0] == pytest.approx(
        color_ops.luminance(rgb)[0], abs=0.02
    )


def test_temperature_warms_red_and_cools_blue():
    rgb = make_rgb((0.5, 0.5, 0.5))
    warmed = color_ops.adjust_temperature(rgb, 1.0)
    assert warmed[0, 0] > rgb[0, 0]
    assert warmed[0, 2] < rgb[0, 2]
    assert warmed[0, 1] == pytest.approx(rgb[0, 1])


def test_contrast_pushes_away_from_middle_gray():
    rgb = make_rgb((0.25, 0.5, 0.75))
    result = color_ops.adjust_contrast(rgb, 2.0)
    assert result[0, 0] == pytest.approx(0.0)
    assert result[0, 1] == pytest.approx(0.5)
    assert result[0, 2] == pytest.approx(1.0)


def test_invert_is_its_own_inverse():
    rgb = make_rgb((0.1, 0.6, 0.9))
    assert np.allclose(color_ops.invert(color_ops.invert(rgb)), rgb)


def test_posterize_snaps_to_discrete_levels():
    rgb = make_rgb((0.1, 0.4, 0.9))
    result = color_ops.posterize(rgb, 2)
    assert set(np.unique(result).tolist()) <= {0.0, 1.0}
