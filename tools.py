"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re
import statistics

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Size matching helpers ─────────────────────────────────────────────────────

def _normalize_size(size_str: str) -> str:
    s = size_str.lower().strip()
    s = re.sub(r'\(.*?\)', '', s).strip()   # remove parenthetical notes
    s = re.sub(r'\bus\s*', '', s).strip()   # remove "us " shoe prefix
    return s


def _size_matches(listing_size: str, listing_category: str, query_size: str) -> bool:
    norm_listing = _normalize_size(listing_size)
    norm_query = _normalize_size(query_size)

    if norm_listing.startswith('one size'):
        return True

    if listing_category == 'bottoms':
        tokens = norm_listing.split()
        return norm_query in tokens or norm_listing == norm_query

    if listing_category == 'shoes':
        return norm_listing == norm_query

    # tops, outerwear, accessories — handle slash ranges (s/m, m/l)
    if '/' in norm_listing:
        return norm_query in norm_listing.split('/')
    return norm_listing == norm_query


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Price filter
    if max_price is not None:
        listings = [item for item in listings if item["price"] <= max_price]

    # Size filter
    if size is not None:
        listings = [
            item for item in listings
            if _size_matches(item["size"], item["category"], size)
        ]

    # Score by keyword overlap against title, description, and style_tags
    query_tokens = set(re.findall(r'[a-z0-9]+', description.lower()))

    def _score(item):
        haystack = (
            item["title"] + " "
            + item["description"] + " "
            + " ".join(item["style_tags"])
        ).lower()
        return sum(1 for token in query_tokens if token in haystack)

    scored = [(item, _score(item)) for item in listings]
    matched = [(item, score) for item, score in scored if score > 0]
    matched.sort(key=lambda x: x[1], reverse=True)
    return [item for item, _ in matched]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    items = wardrobe.get("items", [])
    item_desc = (
        f"Title: {new_item['title']}\n"
        f"Category: {new_item['category']}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}"
    )

    if not items:
        prompt = (
            "You are a personal stylist. The user is considering buying this thrifted item:\n"
            f"{item_desc}\n\n"
            "They haven't shared their wardrobe yet. Suggest general styling ideas: "
            "what item types pair well with this piece, what aesthetic it fits, and how to "
            "build a simple outfit around it. Keep it conversational, 3–5 sentences."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {w['name']} ({w['category']}, {', '.join(w['colors'])})"
            for w in items
        )
        prompt = (
            "You are a personal stylist. The user is considering buying this thrifted item:\n"
            f"{item_desc}\n\n"
            f"Their current wardrobe includes:\n{wardrobe_lines}\n\n"
            "Suggest 1–2 complete outfit combinations using the new item and specific pieces "
            "from their wardrobe above. Name the wardrobe pieces by name. Keep it "
            "conversational, 3–5 sentences."
        )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Can't create a fit card — the outfit description is missing. Please try your search again."

    title = new_item.get("title", "this piece")
    price = new_item.get("price", "")
    platform = new_item.get("platform", "")

    prompt = (
        "You are a fashion-forward social media creator. Write a 2–4 sentence Instagram/TikTok OOTD caption "
        "for the following outfit. The caption must:\n"
        "- Sound casual and authentic, like a real person posting their fit (not a product description)\n"
        "- Mention the item name, price, and platform exactly once each, naturally woven in\n"
        "- Capture the specific vibe of the outfit in concrete terms (avoid generic phrases like 'cute' or 'stylish')\n\n"
        f"Thrifted item: {title} — ${price} on {platform}\n"
        f"Outfit: {outfit}\n\n"
        "Write only the caption text. No hashtags unless they feel truly natural."
    )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    return response.choices[0].message.content or ""


# ── Tool 4: compare_price ─────────────────────────────────────────────────────

_UNKNOWN = {"verdict": "unknown", "reasoning": "No comparable listings found."}


def compare_price(item: dict) -> dict:
    """
    Estimate whether a listing's price is fair relative to similar items
    in the dataset.

    Args:
        item: A listing dict from search_listings. Uses 'category' and 'price'.

    Returns:
        A dict with:
            verdict      (str):   "great deal", "fair price", or "above average"
            median_price (float): Median price of comparable listings
            percentile   (int):   0–100; lower = cheaper relative to category
            reasoning    (str):   1–2 sentence explanation

        Returns {"verdict": "unknown", "reasoning": "No comparable listings found."}
        if category/price are missing or no comparables exist.
    """
    category = item.get("category")
    price = item.get("price")
    if category is None or price is None:
        return _UNKNOWN

    item_id = item.get("id")
    comparables = [
        lst["price"]
        for lst in load_listings()
        if lst["category"] == category and lst.get("id") != item_id
    ]

    if not comparables:
        return _UNKNOWN

    median_price = round(statistics.median(comparables), 2)
    cheaper_count = sum(1 for p in comparables if p < price)
    percentile = round(cheaper_count / len(comparables) * 100)

    if percentile <= 33:
        verdict = "great deal"
    elif percentile <= 66:
        verdict = "fair price"
    else:
        verdict = "above average"

    reasoning = (
        f"This ${price:.0f} {category[:-1] if category.endswith('s') else category} "
        f"is at the {percentile}th percentile of {category} listings in the dataset, "
        f"which have a median price of ${median_price:.0f}."
    )

    return {
        "verdict": verdict,
        "median_price": median_price,
        "percentile": percentile,
        "reasoning": reasoning,
    }
