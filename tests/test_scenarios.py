import pytest

from pv_synth.scenarios import parse_mix_weights, parse_n_by_type


def test_parse_mix_weights_valid() -> None:
    weights = parse_mix_weights("single=0.5,east-west=0.5")
    assert weights == {"single": 0.5, "east-west": 0.5}


def test_parse_mix_weights_invalid_sum() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        parse_mix_weights("single=0.2,east-west=0.2")


def test_parse_n_by_type_valid() -> None:
    counts = parse_n_by_type("single=3,east-west=2")
    assert counts == {"single": 3, "east-west": 2}


def test_parse_n_by_type_invalid_total() -> None:
    with pytest.raises(ValueError, match="at least one system"):
        parse_n_by_type("single=0,east-west=0")
