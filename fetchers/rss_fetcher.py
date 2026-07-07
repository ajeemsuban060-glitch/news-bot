"""
Generic RSS fetcher with escalating lookback window.

If a category doesn't hit MIN_ITEMS_PER_CATEGORY within the first lookback
window (24h), it retries with a wider window (48h, then 72h) before giving up.
No padding with irrelevant stories to force a count.
"""

import time
from datetime import datetime, timezone
from typing import Optional

import feedparser

from .config import LOOKBACK_ESCALATION_HOURS, MIN_ITEMS_PER_CATEGORY


def _entry_timestamp(entry) -> Optional[datetime]:
    """Extract a UTC datetime from a feedparser entry, or None if unavailable."""
    for key in ("published_parsed", "updated_parsed"):
        struct = getattr(entry, key, None)
        if struct:
            return datetime.fromtimestamp(time.mktime(struct), tz=timezone.utc)
    return None


def _fetch_feed(url: str, cutoff: datetime) -> list[dict]:
    """Fetch a single feed, return entries newer than cutoff as plain dicts."""
    parsed = feedparser.parse(url)

    if parsed.bozo and not parsed.entries:
        # Feed is broken/unreachable — fail soft, return empty, let caller move on
        print(f"[WARN] Feed unreachable or malformed: {url} — {parsed.bozo_exception}")
        return []

    items = []
    for entry in parsed.entries:
        ts = _entry_timestamp(entry)
        if ts is None or ts >= cutoff:
            items.append({
                "title": entry.get("title", "").strip(),
                "description": entry.get("summary", entry.get("description", "")).strip(),
                "link": entry.get("link", ""),
                "published": ts.isoformat() if ts else None,
                "source_feed": url,
            })
    return items


def fetch_category(
    feeds: list[str],
    min_items: int = MIN_ITEMS_PER_CATEGORY,
    filter_fn=None,
) -> tuple[list[dict], int]:
    """
    Fetch all feeds for a category, escalating the lookback window until
    min_items is reached (after filter_fn, if given) or all windows are exhausted.

    filter_fn: optional predicate applied to each item BEFORE the min_items
    check, so escalation is aware of downstream filtering (e.g. keyword match).

    Returns (items, lookback_hours_used).
    """
    now = datetime.now(timezone.utc)
    collected: list[dict] = []
    lookback_used = LOOKBACK_ESCALATION_HOURS[0]

    for hours in LOOKBACK_ESCALATION_HOURS:
        cutoff = now.timestamp() - hours * 3600
        cutoff_dt = datetime.fromtimestamp(cutoff, tz=timezone.utc)

        raw = []
        for feed_url in feeds:
            raw.extend(_fetch_feed(feed_url, cutoff_dt))

        collected = [item for item in raw if filter_fn(item)] if filter_fn else raw

        lookback_used = hours
        if len(collected) >= min_items:
            break

    return collected, lookback_used