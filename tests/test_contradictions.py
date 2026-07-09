from backend.scoring.contradictions import (
    contradiction_penalty,
    find_pairwise_contradictions,
    severity_for_gap,
)


def _r(source_id, score, evidence_id=0):
    return {"source_id": source_id, "score": score, "evidence_id": evidence_id}


def test_severity_buckets():
    assert severity_for_gap(10) is None
    assert severity_for_gap(15) == "moderate"
    assert severity_for_gap(25) == "significant"
    assert severity_for_gap(40) == "severe"


def test_penalty_zero_below_threshold():
    assert contradiction_penalty(None) == 0.0
    assert contradiction_penalty(10.0) == 0.0


def test_penalty_grows_and_caps():
    assert 0 < contradiction_penalty(20.0) < contradiction_penalty(30.0)
    assert contradiction_penalty(90.0) == 10.0  # MAX_CONTRADICTION_PENALTY


def test_pairwise_detection():
    ratings = [_r(1, 98.0), _r(2, 70.0), _r(3, 96.0)]
    found = find_pairwise_contradictions(ratings)
    # 98 vs 70 (gap 28, significant) and 96 vs 70 (gap 26, significant); 98 vs 96 is fine.
    assert len(found) == 2
    assert all(c["severity"] == "significant" for c in found)
    assert all(c["score_a"] <= c["score_b"] for c in found)


def test_same_source_never_contradicts_itself():
    assert find_pairwise_contradictions([_r(1, 98.0), _r(1, 60.0)]) == []


def test_agreement_produces_nothing():
    assert find_pairwise_contradictions([_r(1, 90.0), _r(2, 88.0)]) == []
