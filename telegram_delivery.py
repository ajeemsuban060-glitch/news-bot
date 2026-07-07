"""
Telegram delivery for the news digest.

Design:
- One message per category: category header, then each headline (bold)
  immediately followed by its summary, all in a single send.
- All messages use Telegram's MarkdownV2 parse mode.
- Retention: messages aren't deleted on a timer. Instead, every run
  records the message_ids it sends (with today's date) to a small JSON
  state file. On the *next* run, if the stored date is a previous day,
  those old message_ids are deleted before anything new is sent. This
  means a message lives until the following day's run executes, not
  exactly 24h — acceptable for a once-daily cron, but flag if the cron
  is ever skipped since stale messages would then persist longer.
"""

import os
import re
import json
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"

STATE_FILE = Path(__file__).parent / "telegram_state.json"

MAX_RETRIES = 3
DELAY_BETWEEN_MESSAGES_SEC = 0.5  # stay well under Telegram's rate limits

# Reserved characters in Telegram MarkdownV2 that must be escaped in any
# plain text we didn't author ourselves (headlines/summaries from Gemini).
_MDV2_RESERVED = r'_*[]()~`>#+-=|{}.!'


def _escape_markdown_v2(text: str) -> str:
    """Escape MarkdownV2 reserved characters in untrusted/dynamic text."""
    return re.sub(f"([{re.escape(_MDV2_RESERVED)}])", r"\\\1", text)


# ---------------------------------------------------------------------------
# State (for previous-day cleanup)
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {"date": None, "message_ids": []}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[WARN] Failed to read telegram_state.json, treating as empty: {e}")
        return {"date": None, "message_ids": []}


def _save_state(state: dict) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except OSError as e:
        print(f"[ERROR] Failed to write telegram_state.json: {e}")


def _delete_message(message_id: int) -> bool:
    try:
        resp = requests.post(
            f"{API_BASE}/deleteMessage",
            json={"chat_id": CHAT_ID, "message_id": message_id},
            timeout=15,
        )
        data = resp.json()
        if not data.get("ok"):
            print(f"[WARN] Could not delete message {message_id}: {data.get('description')}")
            return False
        return True
    except requests.RequestException as e:
        print(f"[WARN] Network error deleting message {message_id}: {e}")
        return False


def _cleanup_previous_day(state: dict) -> dict:
    """
    If the stored state is from a previous day, delete all of yesterday's
    messages and return a fresh empty state. If it's from today already
    (e.g. a rerun), leave it as-is so new message_ids get appended to it.
    """
    today = date.today().isoformat()

    if state["date"] is None:
        return {"date": today, "message_ids": []}

    if state["date"] == today:
        # Same-day rerun: keep existing ids, we'll append to them.
        return state

    old_ids = state["message_ids"]
    print(f"[INFO] Deleting {len(old_ids)} message(s) from {state['date']} before sending today's digest...")
    deleted = 0
    for mid in old_ids:
        if _delete_message(mid):
            deleted += 1
        time.sleep(DELAY_BETWEEN_MESSAGES_SEC)
    print(f"[INFO] Deleted {deleted}/{len(old_ids)} previous-day messages.")

    return {"date": today, "message_ids": []}


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

def _send_message(text: str, max_retries: int = MAX_RETRIES) -> int | None:
    """
    Send one MarkdownV2 message. Returns the sent message_id, or None if
    it ultimately failed (permanent failure, or retries exhausted).
    """
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(f"{API_BASE}/sendMessage", json=payload, timeout=15)
            data = resp.json()

            if data.get("ok"):
                return data["result"]["message_id"]

            # 400 = malformed request (e.g. bad Markdown escaping) -> permanent,
            # retrying the identical payload will fail identically.
            # 429 = rate limited -> transient, worth a retry with backoff.
            error_code = resp.status_code
            description = data.get("description", "unknown error")

            if error_code == 429 and attempt < max_retries:
                # Telegram sometimes tells us exactly how long to wait.
                retry_after = data.get("parameters", {}).get("retry_after", 2 ** attempt)
                print(f"[WARN] Rate limited by Telegram (attempt {attempt}/{max_retries}) "
                      f"— waiting {retry_after}s")
                time.sleep(retry_after)
                continue

            print(f"[ERROR] Telegram sendMessage failed ({error_code}): {description}")
            return None

        except requests.RequestException as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"[WARN] Network error sending message (attempt {attempt}/{max_retries}): {e} "
                      f"— retrying in {wait}s")
                time.sleep(wait)
            else:
                print(f"[ERROR] Network error sending message after {max_retries} attempts: {e}")
                return None

    return None


def _format_combined_message(label: str, headlines: list[dict]) -> str:
    """
    Single message per category: bolded category header, then each
    headline (bold) immediately followed by its summary. Replaces the
    earlier two-message (headlines-then-details) design per Ajeem's
    preference for one message per topic.
    """
    lines = [f"*{_escape_markdown_v2(label)}*"]
    for i, h in enumerate(headlines, 1):
        headline = _escape_markdown_v2(h["headline"])
        summary = _escape_markdown_v2(h["summary"])
        lines.append(f"*{i}\\. {headline}*\n{summary}")
    return "\n\n".join(lines)


def send_daily_digest(summarized_data: dict) -> None:
    """
    Takes the output of summarizer.summarize_all() and delivers it to
    Telegram: one headline message + one details message per category,
    with previous-day messages cleaned up first.

    summarized_data shape:
        {category_key: {"label": str, "headlines": [{"headline", "summary"}, ...]}, ...}
    """
    state = _load_state()
    state = _cleanup_previous_day(state)

    sent_ids = list(state["message_ids"])

    for key, cat in summarized_data.items():
        headlines = cat["headlines"]
        label = cat["label"]

        if not headlines:
            print(f"[WARN] Skipping {key}: no headlines to send.")
            continue

        message = _format_combined_message(label, headlines)

        # Telegram caps messages at 4096 chars. Combining headline+details
        # into one message per category pushes closer to that limit than
        # the old two-message design did, so guard against silent failure
        # by splitting into headline-batches if it's too long.
        if len(message) > 4096:
            print(f"[WARN] {key}: combined message is {len(message)} chars, "
                  f"over Telegram's 4096 limit — splitting into two messages.")
            mid_point = len(headlines) // 2
            first_half = _format_combined_message(label, headlines[:mid_point])
            second_half = _format_combined_message(f"{label} (cont.)", headlines[mid_point:])
            for part in (first_half, second_half):
                mid = _send_message(part)
                if mid is not None:
                    sent_ids.append(mid)
                time.sleep(DELAY_BETWEEN_MESSAGES_SEC)
            continue

        mid = _send_message(message)
        if mid is not None:
            sent_ids.append(mid)
        else:
            print(f"[ERROR] Failed to send message for {key}.")

        time.sleep(DELAY_BETWEEN_MESSAGES_SEC)

    state["message_ids"] = sent_ids
    _save_state(state)
    print(f"[INFO] Digest delivery complete. {len(sent_ids)} message(s) tracked for cleanup tomorrow.")