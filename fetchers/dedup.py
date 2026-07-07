"""
Dedup layer for RSS items before they reach the summarizer.

Cheap, dependency-free approach: normalize titles and compare using
a token-overlap similarity score. Good enough for same-day news dedup
across a handful of feeds — no need for embeddings here.
"""

import re


def _normalize(title: str) -> set[str]:
    """Lowercase, strip punctuation, return a set of significant words."""
    title = title.lower()
    title = re.sub(r"[^\w\s]", "", title)
    words = title.split()
    stopwords = {
        "the", "a", "an", "to", "of", "in", "on", "for", "and", "is",
        "at", "as", "by", "with", "after", "over", "amid", "says",
    }
    return {w for w in words if w not in stopwords and len(w) > 2}


def _similarity(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two normalized word sets."""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union


def dedup_items(items: list[dict], threshold: float = 0.50, debug: bool = False) -> list[dict]:
    """
    Remove near-duplicate items based on title similarity.

    Keeps the FIRST occurrence of each unique story. Feed order in
    CATEGORY_FEEDS effectively sets priority — put your preferred/
    highest-quality source first in each feed list.

    threshold: Jaccard similarity above which two titles are considered
    the same story.
    debug: if True, prints similarity scores for near-miss pairs so you
    can tune threshold based on real data.
    """
    kept: list[dict] = []
    kept_word_sets: list[set[str]] = []

    for item in items:
        words = _normalize(item["title"])
        best_score = 0.0
        best_match = None
        for i, seen in enumerate(kept_word_sets):
            score = _similarity(words, seen)
            if score > best_score:
                best_score = score
                best_match = kept[i]["title"]

        is_duplicate = best_score >= threshold

        if debug and best_score > 0.15:
            marker = "DUP" if is_duplicate else "keep"
            print(f"[{marker}] {best_score:.2f} | {item['title'][:60]} ~ {best_match[:60] if best_match else ''}")

        if not is_duplicate:
            kept.append(item)
            kept_word_sets.append(words)

    return kept