"""
utils/style_profile.py

Persistent style profile: accumulates style and color preferences across
sessions so the agent can personalise outfit suggestions without the user
re-entering their tastes each time.

Storage: data/style_profile.json (one file, one user)
"""

import json
import os
import copy
from datetime import datetime
from collections import Counter

_PROFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "style_profile.json"
)

_EMPTY_PROFILE = {
    "style_counts": {},
    "color_counts": {},
    "preferred_sizes": {},
    "interaction_count": 0,
    "last_updated": None,
}


def load_profile() -> dict:
    """Return the saved style profile, or a blank skeleton if none exists."""
    try:
        with open(_PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Use deepcopy to prevent mutating the global _EMPTY_PROFILE template
        return copy.deepcopy(_EMPTY_PROFILE)


def save_profile(profile: dict) -> None:
    """Write the profile to disk, stamping last_updated."""
    profile["last_updated"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(_PROFILE_PATH), exist_ok=True)
    with open(_PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)


def top_n(count_dict: dict, n: int = 5) -> list:
    """Return the top-N keys by frequency count, highest first."""
    # Counter's most_common handles the sorting and slicing automatically
    return [k for k, _ in Counter(count_dict).most_common(n)]


def update_profile(profile: dict, session: dict) -> dict:
    """
    Merge signals from a completed session into the profile.

    Extracts style_tags and colors from the selected listing, and updates
    the size map using the item's category + the parsed size from the query.
    Increments all counts.
    """
    # Safely initialize keys to prevent KeyErrors with older JSON files
    profile.setdefault("style_counts", {})
    profile.setdefault("color_counts", {})
    profile.setdefault("preferred_sizes", {})

    item = session.get("selected_item") or {}

    # Use Counter.update() to ingest lists of new tags/colors cleanly
    style_counter = Counter(profile["style_counts"])
    style_counter.update(item.get("style_tags", []))
    profile["style_counts"] = dict(style_counter)

    color_counter = Counter(profile["color_counts"])
    color_counter.update(item.get("colors", []))
    profile["color_counts"] = dict(color_counter)

    category = item.get("category")
    size = (session.get("parsed") or {}).get("size")
    if category and size:
        profile["preferred_sizes"][category] = size

    profile["interaction_count"] = profile.get("interaction_count", 0) + 1

    return profile


def format_profile_summary(profile: dict) -> str:
    """Return a one-line human-readable summary for display in the UI."""
    if not profile.get("interaction_count"):
        return "No style profile yet. Complete a search to build one."

    styles = top_n(profile.get("style_counts", {}))
    colors = top_n(profile.get("color_counts", {}))
    sessions = profile.get("interaction_count", 0)

    parts = []
    if styles:
        parts.append(f"Top styles: {', '.join(styles)}")
    if colors:
        parts.append(f"Top colors: {', '.join(colors)}")
    parts.append(f"Sessions: {sessions}")
    
    return " | ".join(parts)