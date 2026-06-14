"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card, compare_price, get_trends


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "price_comparison": None,    # dict returned by compare_price (stretch)
        "trends": None,              # dict returned by get_trends (stretch)
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse query with regex
    price_match = re.search(r'under\s*\$(\d+(?:\.\d+)?)', query, re.IGNORECASE) \
               or re.search(r'\$(\d+(?:\.\d+)?)', query, re.IGNORECASE)
    max_price = float(price_match.group(1)) if price_match else None

    size_match = re.search(r'\bsize\s+([A-Z0-9]+(?:/[A-Z0-9]+)?)\b', query, re.IGNORECASE)
    size = size_match.group(1) if size_match else None

    description = re.sub(r'under\s*\$\d+(?:\.\d+)?', '', query, flags=re.IGNORECASE)
    description = re.sub(r'\$\d+(?:\.\d+)?', '', description, flags=re.IGNORECASE)
    description = re.sub(r'\bsize\s+\S+', '', description, flags=re.IGNORECASE).strip()

    session["parsed"] = {"description": description, "size": size, "max_price": max_price}

    # Step 3: Search — branch on empty results (do NOT proceed with empty input)
    results = search_listings(description, size, max_price)
    session["search_results"] = results
    if not results:
        price_clause = f" under ${max_price:.0f}" if max_price else ""
        session["error"] = (
            f"No listings found for '{description}'{price_clause}. "
            "Try broadening your description or raising your budget."
        )
        return session

    # Step 4: Select top result
    session["selected_item"] = results[0]

    # Step 5b: Compare price — stretch, non-blocking
    try:
        session["price_comparison"] = compare_price(session["selected_item"])
    except Exception:
        session["price_comparison"] = None

    # Step 5c: Get trends — stretch, non-blocking; result passed into suggest_outfit
    trends = {"trends": [], "source": "unavailable"}
    try:
        trends = get_trends(
            size=size,
            category=session["selected_item"].get("category"),
        )
    except Exception:
        pass
    session["trends"] = trends

    # Step 5: Suggest outfit (with trend context when available)
    try:
        outfit = suggest_outfit(session["selected_item"], session["wardrobe"], trends=trends, user_query=session["parsed"]["description"])
    except Exception:
        session["error"] = (
            "Couldn't generate an outfit suggestion — the styling service is unavailable. "
            "Try again in a moment."
        )
        return session

    if not outfit or not outfit.strip():
        session["error"] = (
            "Couldn't generate an outfit suggestion — the styling service is unavailable. "
            "Try again in a moment."
        )
        return session

    session["outfit_suggestion"] = outfit

    # Step 6: Create fit card
    try:
        session["fit_card"] = create_fit_card(session["outfit_suggestion"], session["selected_item"])
    except Exception:
        session["error"] = (
            "Fit card generation failed. Your outfit suggestion is ready — "
            "the caption couldn't be created this time."
        )
        return session

    # Step 7: Return completed session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
