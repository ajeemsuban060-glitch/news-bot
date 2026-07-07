"""
Gemini-based summarizer. Takes deduped items per category and returns
5 headline+summary pairs per category as structured JSON.

Tamil Nadu politics is handled specially:
- native_tamil source: items are already Tamil, just summarize.
- fallback_translated source: items may be English or mixed, translate
  AND summarize into Tamil in one pass. English proper nouns (party
  names, people, places) are kept as-is rather than transliterated.

Includes retry with backoff for transient network errors (DNS blips,
dropped connections), since hammering 7 calls back-to-back can trigger
rate-limit-adjacent failures on the free tier.
"""

import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL = "gemini-2.5-flash"
HEADLINES_PER_CATEGORY = 5
MAX_RETRIES = 3
DELAY_BETWEEN_CATEGORIES_SEC = 1

# Gemini 2.5 Flash reserves part of its output budget for internal
# "thinking" tokens by default. For a deterministic summarization task
# like this, that thinking is wasted spend and risks the final JSON
# getting cut off mid-string before it's done (exactly what happened to
# the geopolitics category — the response was truncated, not malformed).
# thinking_budget=0 disables it; response_mime_type forces valid JSON
# directly instead of relying on markdown-fence stripping.
GENERATION_CONFIG = types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(thinking_budget=0),
    response_mime_type="application/json",
    max_output_tokens=2048,
)


def _build_prompt(category_label: str, items: list[dict], is_tamil_output: bool) -> str:
    """Build the summarization prompt for one category's items."""
    # Use .get() with fallbacks — malformed RSS entries missing a title or
    # description should degrade gracefully, not crash the whole category.
    items_text = "\n".join(
        f"{i+1}. {item.get('title', '(untitled)')} — {(item.get('description') or '')[:200]}"
        for i, item in enumerate(items)
    )

    if is_tamil_output:
        instruction = (
            "Summarize the top stories below in TAMIL language only. "
            "If any source text is in English, translate it into Tamil. "
            "Keep proper nouns (party names like DMK, AIADMK, NTK, people's "
            "names, places) in their original English/Roman script — do not "
            "transliterate them into Tamil script. "
            "Pick the 5 most significant, distinct stories. Avoid picking "
            "near-duplicate stories about the same specific event."
        )
    else:
        instruction = (
            "Summarize the top stories below in English. "
            "Pick the 5 most significant, distinct stories. Avoid picking "
            "near-duplicate stories about the same specific event."
        )

    return f"""{instruction}

Category: {category_label}

Source articles:
{items_text}

Return ONLY valid JSON, no markdown fences, no preamble, in this exact format:
{{
  "headlines": [
    {{"headline": "short headline", "summary": "1-2 sentence summary"}},
    ...
  ]
}}
Return exactly {HEADLINES_PER_CATEGORY} items, or fewer if there aren't enough distinct stories."""


def _parse_response(text: str) -> list[dict]:
    """Strip potential markdown fences and parse JSON safely."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        headlines = parsed.get("headlines", [])
    except json.JSONDecodeError as e:
        print(f"[WARN] Failed to parse Gemini response as JSON: {e}")
        print(f"[WARN] Raw response: {text[:300]}")
        return []

    # Schema check: don't trust Gemini's JSON blindly. Drop any entry
    # missing required keys instead of letting a downstream KeyError
    # (e.g. in the Telegram formatter) take out the whole category.
    valid = [
        h for h in headlines
        if isinstance(h, dict) and "headline" in h and "summary" in h
    ]
    if len(valid) != len(headlines):
        print(f"[WARN] Dropped {len(headlines) - len(valid)} malformed "
              f"headline entr{'y' if len(headlines) - len(valid) == 1 else 'ies'} (missing required keys)")
    return valid


def _is_retryable(e: Exception) -> bool:
    """
    Distinguish transient failures (worth retrying) from permanent ones
    (retrying is just wasted time + backoff delay).

    - genai_errors.APIError with code 429 (rate limit) or 5xx (server-side
      transient) -> retryable.
    - genai_errors.APIError with anything else (400 bad request, 401/403
      auth, 404) -> permanent, don't waste retries.
    - Any other exception (e.g. raw network/socket/DNS errors that don't
      surface as APIError) -> assume transient, retry.
    """
    if isinstance(e, genai_errors.APIError):
        code = getattr(e, "code", None)
        return code == 429 or (isinstance(code, int) and 500 <= code < 600)
    return True


def summarize_category(category_key: str, category_data: dict, max_retries: int = MAX_RETRIES) -> list[dict]:
    """
    Summarize one category's deduped items into structured headlines.
    Retries on transient network errors before giving up.

    Returns list of {"headline": str, "summary": str} dicts.
    """
    items = category_data["items"]
    if not items:
        return []

    is_tamil_output = category_key == "tamil_nadu_politics"
    prompt = _build_prompt(category_data["label"], items, is_tamil_output)

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=GENERATION_CONFIG,
            )
            return _parse_response(response.text)
        except Exception as e:
            if not _is_retryable(e):
                print(f"[ERROR] Non-retryable Gemini error for {category_key}, "
                      f"giving up immediately: {e}")
                return []

            if attempt < max_retries:
                wait = 2 ** attempt  # 2s, 4s, 8s
                print(f"[WARN] Gemini call failed for {category_key} "
                    f"(attempt {attempt}/{max_retries}): {e} — retrying in {wait}s")
                time.sleep(wait)
            else:
                print(f"[ERROR] Gemini call failed for {category_key} "
                    f"after {max_retries} attempts: {e}")
                return []


def summarize_all(fetched_data: dict) -> dict:
    """
    Takes the output of fetch_all_categories() and returns:
        {
            category_key: {
                "label": str,
                "headlines": [{"headline": ..., "summary": ...}, ...],
            },
            ...
        }
    """
    results = {}
    for key, cat in fetched_data.items():
        print(f"[INFO] Summarizing {key} ({len(cat['items'])} items)...")
        headlines = summarize_category(key, cat)
        results[key] = {
            "label": cat["label"],
            "headlines": headlines,
        }
        if not headlines:
            print(f"[WARN] {key}: no headlines produced.")
        time.sleep(DELAY_BETWEEN_CATEGORIES_SEC)
    return results