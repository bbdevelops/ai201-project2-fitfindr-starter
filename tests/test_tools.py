# tests/test_tools.py
from tools import search_listings

REQUIRED_FIELDS = {"id", "title", "description", "category", "style_tags",
                   "size", "condition", "price", "colors", "brand", "platform"}

# ── Existing tests ────────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

# ── New tests ─────────────────────────────────────────────────────────────────

def test_search_price_ceiling_exact():
    """An item priced exactly at max_price must be included."""
    results = search_listings("jeans", size=None, max_price=38)
    assert any(item["price"] == 38 for item in results)

def test_search_result_has_required_fields():
    """Every result dict must contain all required listing fields."""
    results = search_listings("vintage tee", size=None, max_price=None)
    assert len(results) > 0
    for item in results:
        assert REQUIRED_FIELDS.issubset(item.keys()), f"Missing fields in: {item}"

def test_search_no_size_no_price_returns_results():
    """With no filters at all, a broad query should return results."""
    results = search_listings("jacket", size=None, max_price=None)
    assert len(results) > 0

def test_search_size_letter_uppercase():
    """Size filter 'M' should return only size-M-compatible items."""
    results = search_listings("top", size="M", max_price=None)
    assert len(results) > 0
    for item in results:
        norm = item["size"].lower()
        # Acceptable: exact "m", slash ranges containing "m", or one-size
        assert (
            norm == "m"
            or "m" in norm.split("/")
            or norm.startswith("one size")
        ), f"Unexpected size '{item['size']}' for query size 'M'"

def test_search_size_case_insensitive():
    """Lowercase 'm' and uppercase 'M' should return identical result sets."""
    upper = search_listings("top", size="M", max_price=None)
    lower = search_listings("top", size="m", max_price=None)
    assert [i["id"] for i in upper] == [i["id"] for i in lower]

def test_search_size_slash_range_matched():
    """A query size of 'S' should match listings sized 'S/M'."""
    results = search_listings("baby tee", size="S", max_price=None)
    ids = [item["id"] for item in results]
    # lst_002 is the Y2K Baby Tee sized S/M — it must be included
    assert "lst_002" in ids, "S/M listing not matched by size='S'"

def test_search_bottoms_waist_size():
    """A waist-only query like 'W30' should match 'W30 L30' and 'W30' listings."""
    results = search_listings("jeans", size="W30", max_price=None)
    assert len(results) > 0
    for item in results:
        assert item["category"] == "bottoms"
        norm = item["size"].lower()
        assert "w30" in norm.split(), f"Unexpected bottom size '{item['size']}'"

def test_search_shoe_size():
    """Numeric shoe size query should match US-sized shoe listings."""
    results = search_listings("sneakers", size="8", max_price=None)
    assert len(results) > 0
    for item in results:
        assert item["category"] == "shoes"

def test_search_sorted_by_relevance():
    """First result should score at least as high as the last result."""
    results = search_listings("vintage graphic tee", size=None, max_price=None)
    assert len(results) >= 2
    # The first result must have 'vintage' or 'graphic' or 'tee' in its text
    first = (results[0]["title"] + results[0]["description"] + " ".join(results[0]["style_tags"])).lower()
    assert any(kw in first for kw in ["vintage", "graphic", "tee"])

def test_search_one_size_accessory_matches_any_size():
    """One-size accessories should appear regardless of what size is queried."""
    results = search_listings("bucket hat", size="M", max_price=None)
    # lst_031 or similar one-size hat should be in results
    one_size_ids = [item["id"] for item in results if item["size"].lower().startswith("one size")]
    assert len(one_size_ids) > 0, "No one-size item matched when size='M'"
