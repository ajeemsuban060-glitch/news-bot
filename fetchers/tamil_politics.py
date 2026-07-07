"""
Category 6 special handling: Tamil Nadu politics, output in Tamil.

Primary (Option B): native Tamil feed, filtered to political stories by keyword.
Fallback (Option A): English TN feeds, translated later by the summarizer step.

The fallback path is automatic — if the primary yields too few items after
filtering, we fall through silently and mark which path was used so the
summarizer knows whether translation is needed.
"""
from .config import CATEGORY_FEEDS, MIN_ITEMS_PER_CATEGORY, TAMIL_POLITICS_KEYWORDS
from .rss_fetcher import fetch_category


def _matches_politics(item: dict) -> bool:
    text = f"{item['title']} {item['description']}"
    return any(keyword in text for keyword in TAMIL_POLITICS_KEYWORDS)


def fetch_tamil_nadu_politics() -> dict:
    cfg = CATEGORY_FEEDS["tamil_nadu_politics"]

    # Primary: native Tamil feed, escalation is now filter-aware
    filtered, lookback = fetch_category(
        cfg["feeds"],
        min_items=MIN_ITEMS_PER_CATEGORY,
        filter_fn=_matches_politics,
    )

    if len(filtered) >= MIN_ITEMS_PER_CATEGORY:
        return {
            "items": filtered,
            "source_path": "native_tamil",
            "lookback_hours": lookback,
        }

    print("[INFO] Native Tamil politics feed thin after filtering "
        f"({len(filtered)} items) — falling back to translated English sources.")

    fallback_items, fallback_lookback = fetch_category(
        cfg["fallback_feeds"], min_items=MIN_ITEMS_PER_CATEGORY
    )

    combined = filtered + fallback_items

    return {
        "items": combined,
        "source_path": "fallback_translated",
        "lookback_hours": max(lookback, fallback_lookback),
    }