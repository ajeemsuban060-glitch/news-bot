"""
Main entry point for the daily news digest pipeline:
    fetch (per category) -> dedup -> summarize (Gemini) -> deliver (Telegram)

Run with:
    python main.py                 # normal run (only in GitHub Actions)
    TEST_MODE=1 python main.py     # local/manual testing — see telegram_delivery.py

This is the script the GitHub Actions cron job will invoke.

TEST_MODE exists because telegram_state.json is only committed/pushed back
to GitHub from inside the Actions workflow. Any local run that touches the
real chat and real state file without that push step creates orphaned
messages the cleanup logic can never find again. TEST_MODE=1 forces all
local/manual runs onto a separate test chat and skips state tracking
entirely, so they can never corrupt production state.
"""

import os
import sys

from fetchers import fetch_all_categories
from summarizer import summarize_all
from telegram_delivery import send_daily_digest

TEST_MODE = os.environ.get("TEST_MODE") == "1"


def main() -> int:
    if TEST_MODE:
        print("[MAIN] TEST_MODE=1 - using test chat, state tracking disabled.")

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
