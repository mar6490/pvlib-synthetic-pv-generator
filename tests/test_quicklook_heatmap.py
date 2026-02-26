import numpy as np

from pv_synth.quicklook import _heatmap_extent_from_minute_index


def test_heatmap_extent_for_15_minute_index() -> None:
    minute_index = np.arange(0, 1440, 15)
    y0, y1, step = _heatmap_extent_from_minute_index(minute_index)

    assert int(minute_index.max()) == 1425
    assert step == 15
    assert y0 == 0.0
    assert y1 == 1440.0


def test_heatmap_extent_for_5_and_1_minute_index() -> None:
    minute_index_5 = np.arange(0, 1440, 5)
    y0_5, y1_5, step_5 = _heatmap_extent_from_minute_index(minute_index_5)
    assert step_5 == 5
    assert y0_5 == 0.0
    assert y1_5 == 1440.0

    minute_index_1 = np.arange(0, 1440, 1)
    y0_1, y1_1, step_1 = _heatmap_extent_from_minute_index(minute_index_1)
    assert step_1 == 1
    assert y0_1 == 0.0
    assert y1_1 == 1440.0
