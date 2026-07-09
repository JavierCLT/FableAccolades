"""Deterministic keyword mapping from customer text to scoring dimensions.

Collectors use this to attribute Reddit/forum posts to dimensions. Keyword-based on
purpose: reproducible, auditable, and cheap. An LLM can optionally refine ambiguous
cases (classification only), but is never required.
"""

from __future__ import annotations

import re

# Ordered: earlier entries win ties (more specific first).
DIMENSION_KEYWORDS: list[tuple[str, list[str]]] = [
    ("cash_yield", ["sweep", "apy", "money market", "spaxx", "vmfxx", "swvxx", "uninvested cash", "cash yield", "interest on cash", "idle cash"]),
    ("transfer_acat", ["acat", "transfer out", "outgoing transfer", "transfer fee", "account transfer", "transferring my account"]),
    ("retirement_rollover", ["ira", "rollover", "401k", "401(k)", "roth", "retirement", "rmd"]),
    ("fractional_shares", ["fractional", "partial share", "dollar-based", "stock slices"]),
    ("banking_integration", ["checking", "debit", "atm", "bill pay", "direct deposit", "cash management account", "bank account"]),
    ("advisory_options", ["robo", "advisor", "advisory", "managed account", "managed portfolio", "financial planner"]),
    ("mobile_app", ["app", "mobile", "android", "ios", "iphone"]),
    ("trading_tools", ["thinkorswim", "tws", "power etrade", "active trader", "options chain", "level 2", "charting", "order type", "trading platform", "paper trading", "api"]),
    ("research_education", ["research", "screener", "education", "learning", "analyst", "morningstar", "news feed"]),
    ("reliability", ["outage", "downtime", "down again", "crash", "can't log in", "cannot log in", "login issues", "server error", "unavailable"]),
    ("security", ["2fa", "two-factor", "hacked", "fraud", "phishing", "locked account", "account locked", "frozen account", "security"]),
    ("tax_reporting", ["1099", "tax lot", "cost basis", "wash sale", "tax form", "tax document", "spec id", "specid"]),
    ("customer_support", ["customer service", "support", "phone", "hold time", "wait time", "representative", "call center", "chat support", "branch"]),
    ("costs_fees", ["fee", "fees", "commission", "margin rate", "expense ratio", "pricing", "cost", "charge"]),
    ("product_breadth", ["crypto", "futures", "forex", "international", "bond", "cds", "mutual fund", "otc", "penny stock"]),
    ("ease_of_use", ["ui", "ux", "interface", "website", "easy to use", "confusing", "intuitive", "clunky", "navigation", "onboarding"]),
]


def classify_dimension(text: str) -> str | None:
    """Return the best-matching dimension slug for a piece of text, or None."""
    t = text.lower()
    best: tuple[int, str] | None = None
    for dim, keywords in DIMENSION_KEYWORDS:
        hits = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", t) or kw in t)
        if hits and (best is None or hits > best[0]):
            best = (hits, dim)
    return best[1] if best else None
