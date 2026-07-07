"""
Main entry point for the daily news digest pipeline:
    fetch (per category) -> dedup -> summarize (Gemini) -> deliver (Telegram)

Run with:
    python main.py

This is the script the GitHub Actions cron job will invoke.
"""

import sys

from fetchers import fetch_all_categories
from summarizer import summarize_all
from telegram_delivery import send_daily_digest


def main() -> int:
    print("[MAIN] Fetching + deduping all categories...")
    fetched = fetch_all_categories()

    if not fetched:
        print("[MAIN] FATAL: fetch_all_categories() returned nothing. Aborting.")
        return 1

    print(f"[MAIN] Fetched {len(fetched)} categories.")

    print("[MAIN] Summarizing via Gemini...")
    summarized = summarize_all(fetched)

    empty_categories = [k for k, v in summarized.items() if not v["headlines"]]
    if empty_categories:
        print(f"[MAIN] WARNING: {len(empty_categories)} categories produced no headlines "
            f"and will be skipped in delivery: {empty_categories}")

    if all(not v["headlines"] for v in summarized.values()):
        print("[MAIN] FATAL: every category failed to summarize. Aborting before delivery.")
        return 1

    print("[MAIN] Delivering to Telegram...")
    send_daily_digest(summarized)

    print("[MAIN] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())