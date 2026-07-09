"""Deterministic normalization of published expert ratings to a common 0-100 scale."""

from __future__ import annotations


def normalize_rating(rating_raw: float, scale_max: float) -> float:
    """Linear rescale of a published rating to 0-100.

    Example: 4.5 / 5.0 -> 90.0. Raises on out-of-range input rather than clamping,
    because an out-of-range published rating means a data-entry or parsing error.
    """
    if scale_max <= 0:
        raise ValueError("scale_max must be positive")
    if rating_raw < 0 or rating_raw > scale_max:
        raise ValueError(f"rating {rating_raw} outside 0..{scale_max}")
    return round(rating_raw / scale_max * 100.0, 2)
