from datetime import date

from backend.scoring.confidence import confidence_score, recency_weight


def test_recency_weight_decays():
    today = date(2026, 7, 9)
    fresh = recency_weight("2026-07-01", today)
    old = recency_weight("2023-07-01", today)
    assert 0.9 < fresh <= 1.0
    assert old < fresh
    assert recency_weight(None, today) == 0.5  # unknown dates get a neutral weight


def test_more_evidence_more_confidence():
    kwargs = dict(avg_quality=0.8, avg_recency=0.9, components_present=3, expert_gap=5.0)
    low = confidence_score(evidence_count=1, **kwargs)
    high = confidence_score(evidence_count=8, **kwargs)
    assert high > low


def test_disagreement_lowers_confidence():
    kwargs = dict(evidence_count=6, avg_quality=0.8, avg_recency=0.9, components_present=3)
    agree = confidence_score(expert_gap=2.0, **kwargs)
    disagree = confidence_score(expert_gap=30.0, **kwargs)
    assert agree > disagree


def test_bounded_0_100():
    assert confidence_score(evidence_count=100, avg_quality=1.0, avg_recency=1.0,
                            components_present=3, expert_gap=0.0) <= 100.0
    assert confidence_score(evidence_count=0, avg_quality=0.0, avg_recency=0.0,
                            components_present=0, expert_gap=None) >= 0.0
