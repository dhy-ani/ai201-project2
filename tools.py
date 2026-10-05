"""
The three FitFindr tools.

    search_listings(description, size, max_price)  -> list[dict]
    suggest_outfit(new_item, wardrobe)             -> str
    create_fit_card(outfit, new_item)              -> str
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings


# ── helpers ───────────────────────────────────────────────────────────────────

def _tokens(text) -> set[str]:
    """Lowercase word tokens, with a trailing plural 's' stripped ('tees' -> 'tee')."""
    words = re.findall(r"[a-z0-9]+", str(text or "").lower())
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words}


def _size_matches(wanted: str, listing_size: str) -> bool:
    """
    Token match, not substring. "M" matches "S/M" but "S" does not match "US 9",
    and "L" does not match "XL".
    """
    want = set(re.findall(r"[a-z0-9]+", str(wanted).lower()))
    have = set(re.findall(r"[a-z0-9]+", str(listing_size or "").lower()))
    return bool(want) and want <= have


def _describe_wardrobe_item(item) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        name = item.get("name") or item.get("title") or item.get("category") or "item"
        extras = [str(item[k]) for k in ("colors", "color", "style_tags") if item.get(k)]
        return f"{name} ({', '.join(extras)})" if extras else str(name)
    return str(item)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Filter listings by size (token match) and max_price (inclusive), score the
    rest by keyword overlap with `description`, and return the best matches.

    Returns a list of listing dicts, best match first, at most
    config.SEARCH_RESULT_LIMIT long. Returns [] when nothing matches.
    """
    wanted = _tokens(description)
    scored = []

    for item in load_listings():
        if max_price is not None and float(item["price"]) > float(max_price):
            continue
        if size and not _size_matches(size, item.get("size")):
            continue

        title_words = _tokens(item.get("title"))
        other_words = _tokens(" ".join(
            str(item.get(k) or "")
            for k in ("description", "category", "brand")
        ))
        other_words |= _tokens(" ".join(item.get("style_tags") or []))
        other_words |= _tokens(" ".join(item.get("colors") or []))

        # A title hit counts double.
        score = sum(
            2 if w in title_words else 1
            for w in wanted
            if w in title_words | other_words
        )
        if score == 0:
            continue
        scored.append((score, float(item["price"]), item))

    scored.sort(key=lambda r: (-r[0], r[1]))
    return [r[2] for r in scored][: config.SEARCH_RESULT_LIMIT]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Ask the model for one or two outfits built around new_item.

    With wardrobe items: specific combinations naming pieces the user owns.
    With an empty wardrobe: general styling advice. Always a non-empty string.
    """
    item_line = (
        f"{new_item.get('title')} "
        f"({new_item.get('category')}, {new_item.get('condition')}, "
        f"colors: {', '.join(new_item.get('colors') or []) or 'n/a'})"
    )
    owned = (wardrobe or {}).get("items") or []

    if owned:
        pieces = "\n".join(f"- {_describe_wardrobe_item(w)}" for w in owned)
        prompt = (
            f"I just found this secondhand piece: {item_line}.\n"
            f"Here is what I already own:\n{pieces}\n\n"
            "Suggest one or two outfits built around the new piece. Name the "
            "specific pieces I own that go with it. Keep it short and plain."
        )
    else:
        prompt = (
            f"I just found this secondhand piece: {item_line}.\n"
            "I haven't listed my wardrobe, so give general styling advice: one "
            "or two outfit ideas using common basics. Keep it short and plain."
        )

    reply = (generate(prompt) or "").strip()
    return reply or f"Style the {new_item.get('title')} with simple basics like jeans and clean sneakers."


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would post about the find.
    Returns a descriptive message (not an exception) if `outfit` is empty.
    """
    if not outfit or not str(outfit).strip():
        return "No outfit to write a caption for yet. Run suggest_outfit first."

    prompt = (
        "Write a caption for a social post about a thrift find. Sound like a "
        "real person, not an ad.\n"
        f"Item: {new_item.get('title')}\n"
        f"Price: ${float(new_item['price']):g}\n"
        f"Platform: {new_item.get('platform')}\n"
        f"Outfit: {outfit}\n\n"
        "Mention the item, the price, and the platform once each. Two short "
        "sentences, under 200 characters total. Be specific about the vibe. "
        "Return only the caption."
    )
    return (generate(prompt) or "").strip()