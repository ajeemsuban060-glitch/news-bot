"""
Fetch all 7 categories, then dedup each category's items before returning.
Summarization and sending are separate pipeline stages (summarizer.py,
telegram_sender.py) built next.
"""
from .config import CATEGORY_FEEDS, MIN_ITEMS_PER_CATEGORY
from .rss_fetcher import fetch_category
from .tamil_politics import fetch_tamil_nadu_politics
from .dedup import dedup_items


def fetch_all_categories() -> dict:
    """
    Returns:
        {
            category_key: {
                "label": str,
                "items": [...],          # post-dedup
                "lookback_hours": int,
                "source_path": str,      # only meaningful for tamil_nadu_politics
            },
            ...
        }
    """
    results = {}
    for key, cfg in CATEGORY_FEEDS.items():
        if key == "tamil_nadu_politics":
            r = fetch_tamil_nadu_politics()
            items = r["items"]
            lookback = r["lookback_hours"]
            source_path = r["source_path"]
        else:
            items, lookback = fetch_category(cfg["feeds"], min_items=MIN_ITEMS_PER_CATEGORY)
            source_path = "native_english"

        pre_dedup_count = len(items)
        items = dedup_items(items)
        if pre_dedup_count != len(items):
            print(f"[INFO] {key}: deduped {pre_dedup_count} -> {len(items)} items")

        results[key] = {
            "label": cfg["label"],
            "items": items,
            "lookback_hours": lookback,
            "source_path": source_path,
        }

        if len(results[key]["items"]) < MIN_ITEMS_PER_CATEGORY:
            print(f"[WARN] {key}: only {len(results[key]['items'])} items "
                f"even after escalating to {results[key]['lookback_hours']}h lookback "
                f"and dedup.")

    return results


if __name__ == "__main__":
    data = fetch_all_categories()
    for key, cat in data.items():
        print(f"\n=== {cat['label']} ({len(cat['items'])} items, "
            f"{cat['lookback_hours']}h lookback, source: {cat['source_path']}) ===")
        for item in cat["items"][:5]:
            print(f"  - {item['title']}")