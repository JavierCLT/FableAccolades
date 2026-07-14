import pytest

from backend.normalizers.expert_ratings import normalize_rating


def test_five_scale():
    assert normalize_rating(4.5, 5.0) == 90.0
    assert normalize_rating(0, 5.0) == 0.0
    assert normalize_rating(5.0, 5.0) == 100.0


def test_ten_scale():
    assert normalize_rating(8.7, 10.0) == 87.0


def test_out_of_range_rejected():
    with pytest.raises(ValueError):
        normalize_rating(5.5, 5.0)
    with pytest.raises(ValueError):
        normalize_rating(-1, 5.0)
    with pytest.raises(ValueError):
        normalize_rating(3, 0)
