"""Deterministic, lexicon-based sentiment classification for customer text.

Used by collectors to label raw Reddit/forum text before theme aggregation.
An LLM may optionally be plugged in for the same task (classification only — it never
produces scores), but the default path is fully deterministic and reproducible.
"""

from __future__ import annotations

import re

POSITIVE_TERMS = {
    "love", "loves", "loved", "great", "excellent", "best", "solid", "reliable", "smooth",
    "easy", "helpful", "recommend", "recommended", "happy", "satisfied", "fast", "responsive",
    "impressed", "fantastic", "awesome", "seamless", "painless", "trustworthy", "generous",
}
NEGATIVE_TERMS = {
    "hate", "terrible", "awful", "worst", "scam", "fraud", "avoid", "slow", "broken", "bug",
    "buggy", "glitch", "outage", "down", "crash", "locked", "frozen", "stuck", "delay",
    "delayed", "nightmare", "horrible", "useless", "frustrating", "frustrated", "angry",
    "complaint", "unresponsive", "hold", "waiting", "denied", "hidden", "fee", "fees",
    "predatory", "misleading", "outdated", "clunky",
}
NEGATORS = {"not", "no", "never", "hardly", "isn't", "wasn't", "don't", "doesn't", "didn't", "can't"}

_TOKEN_RE = re.compile(r"[a-z']+")


def score_text(text: str) -> float:
    """Return a signed sentiment score in [-1, 1] using term counts with simple negation."""
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        return 0.0
    score = 0
    for i, tok in enumerate(tokens):
        negated = i > 0 and tokens[i - 1] in NEGATORS
        if tok in POSITIVE_TERMS:
            score += -1 if negated else 1
        elif tok in NEGATIVE_TERMS:
            score += 1 if negated else -1
    # Normalize by a soft cap so long rants don't dominate.
    denom = max(3.0, len(tokens) / 15.0)
    return max(-1.0, min(1.0, score / denom))


def label_text(text: str, *, pos_threshold: float = 0.15, neg_threshold: float = -0.15) -> str:
    """Map text to 'positive' | 'negative' | 'mixed'."""
    s = score_text(text)
    if s >= pos_threshold:
        return "positive"
    if s <= neg_threshold:
        return "negative"
    return "mixed"
