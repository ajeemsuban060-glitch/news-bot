"""
Quick manual test — run from the news-bot/ root directory:
    python test_fetch.py

Prints item counts, lookback window used, and source path per category,
plus the first 3 headlines so you can eyeball feed quality.
"""

from fetchers import fetch_all_categories

if __name__ == "__main__":
    data = fetch_all_categories()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for key, cat in data.items():
        status = "OK" if len(cat["items"]) >= 5 else "THIN"
        print(f"\n[{status}] {cat['label']}")
        print(f"    items: {len(cat['items'])} | lookback: {cat['lookback_hours']}h | source: {cat['source_path']}")
        for item in cat["items"][:3]:
            print(f"    - {item['title']}")