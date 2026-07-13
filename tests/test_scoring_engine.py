import math
from datetime import date

from backend.scoring.engine import (
    blend_components,
    cfpb_friction_score,
    customer_component_score,
    customer_signal,
)


def _theme(sentiment, volume=10, severity=2, observed="2026-06-01", quality=0.7):
    return {
        "sentiment": sentiment, "volume": volume, "severity": severity,
        "observed_date": observed, "quality_weight": quality,
    }


def test_blend_renormalizes_missing_components():
    # Only expert available -> score equals expert.
    assert blend_components(None, None, 80.0) == 80.0
    # All present -> documented 45/35/20 blend.
    expected = 0.45 * 90 + 0.35 * 60 + 0.20 * 70
    assert math.isclose(blend_components(90.0, 60.0, 70.0), expected)
    assert blend_components(None, None, None) is None


def test_customer_component_neutral_is_50():
    assert customer_component_score([]) is None
    only_mixed = customer_component_score([_theme("mixed")], date(2026, 7, 9))
    assert math.isclose(only_mixed, 50.0)


def test_customer_component_directionality():
    today = date(2026, 7, 9)
    pos = customer_component_score([_theme("positive", volume=40)], today)
    neg = customer_component_score([_theme("negative", volume=40, severity=4)], today)
    assert pos > 50 > neg


def test_severity_amplifies_complaints():
    today = date(2026, 7, 9)
    mild = customer_signal([_theme("negative", severity=1)], today)
    severe = customer_signal([_theme("negative", severity=5)], today)
    assert severe < mild < 0


def test_old_themes_decay():
    today = date(2026, 7, 9)
    recent = customer_signal([_theme("negative", observed="2026-06-01")], today)
    ancient = customer_signal([_theme("negative", observed="2021-02-01")], today)
    assert abs(ancient) < abs(recent)


def test_cfpb_friction_never_guesses_denominator():
    assert cfpb_friction_score(100, None) is None
    assert cfpb_friction_score(100, 0) is None


def test_cfpb_friction_scales_with_rate():
    low_rate = cfpb_friction_score(10, 10000)   # 0.001 complaints per $B
    high_rate = cfpb_friction_score(1500, 255)  # ~5.9 complaints per $B
    assert low_rate > high_rate
    assert high_rate >= 10.0  # floor
