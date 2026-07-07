"""
Integration test for summarizer.py.

Runs the full pipeline: fetch -> dedup -> summarize, for all configured
categories, and prints a pass/fail report per category so failures are
visible instead of silent.

Run with:
    python test_summarize.py
"""

import sys
from summarizer import summarize_all

# This project's fetch layer already builds deduped per-category data
# (see fetchers/__init__.py, rss_fetcher.py, dedup.py). Import the
# real aggregator here instead of duplicating fetch logic in a test.
from fetchers import fetch_all_categories


def main() -> int:
    print("[TEST] Fetching + deduping all categories...")
    fetched = fetch_all_categories()

    if not fetched:
        print("[FAIL] fetch_all_categories() returned no categories at all.")
        return 1

    print(f"[TEST] Got {len(fetched)} categories: {list(fetched.keys())}")
    print("[TEST] Running summarize_all()...\n")

    results = summarize_all(fetched)

    failures = []
    for key, result in results.items():
        headline_count = len(result["headlines"])
        status = "PASS" if headline_count > 0 else "FAIL"
        print(f"[{status}] {key} ({result['label']}): {headline_count} headlines")

        if headline_count == 0:
            failures.append(key)
        else:
            # Print the first headline as a sanity spot-check.
            first = result["headlines"][0]
            print(f"       e.g. \"{first['headline']}\" — {first['summary'][:80]}")

    print()
    if failures:
        print(f"[SUMMARY] {len(failures)}/{len(results)} categories FAILED: {failures}")
        return 1

    print(f"[SUMMARY] All {len(results)} categories summarized successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())