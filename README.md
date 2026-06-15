# FitFindr

FitFindr is a multi-tool AI agent that helps users find secondhand clothing and figure out how to wear it. It searches mock thrift listings, generates outfit combinations using an LLM, and produces a shareable fit card. All while handling failures at each step rather than crashing or silently degrading.

## Demo Video
https://vimeo.com/1201310169

---

## Setup

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# or: .venv\Scripts\activate    # Windows CMD

pip install -r requirements.txt
```

Create a `.env` file in the repo root (never commit it):
```
GROQ_API_KEY=your_key_here
```

Run the app:
```bash
python app.py
```

Open the URL shown in the terminal (usually `http://localhost:7860`).

---

## Tools

### 1. `search_listings`

```python
search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]
```

**Purpose:** Keyword-searches the mock listings dataset and returns matching items sorted by relevance score.

| Parameter | Type | Meaning |
|---|---|---|
| `description` | `str` | Natural language query matched against `title`, `description`, and `style_tags` |
| `size` | `str \| None` | Size filter (e.g. `"M"`, `"W30"`, `"8"`). `None` skips size filtering. Category-aware: slash ranges (`S/M`), waist tokens (`W30 L30`), shoe prefix stripping (`US 8` → `8`), and `One Size` always matches |
| `max_price` | `float \| None` | Inclusive price ceiling in USD. `None` skips price filtering |

**Returns:** `list[dict]` — each dict is a listing with fields: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Returns `[]` on no match; never raises.

---

### 2. `suggest_outfit`

```python
suggest_outfit(
    new_item: dict,
    wardrobe: dict,
    trends: dict | None = None,
    user_query: str | None = None,
    style_profile: dict | None = None
) -> str
```

**Purpose:** Calls the Groq LLM to generate 1–2 outfit combinations pairing the thrifted item with pieces from the user's wardrobe.

| Parameter | Type | Meaning |
|---|---|---|
| `new_item` | `dict` | Listing dict from `search_listings` |
| `wardrobe` | `dict` | Dict with an `items` key containing wardrobe item dicts. Empty list or missing key both handled |
| `trends` | `dict \| None` | Return value of `get_trends`; trend keywords are appended to the LLM prompt when non-empty |
| `user_query` | `str \| None` | Original description string; included in the prompt for context |
| `style_profile` | `dict \| None` | Accumulated style preferences; top-5 tags and colors injected into the prompt |

**Returns:** Non-empty `str` with outfit suggestions. On empty wardrobe, returns general styling advice instead of failing.

---

### 3. `create_fit_card`

```python
create_fit_card(outfit: str, new_item: dict) -> str
```

**Purpose:** Generates a 2–4 sentence casual OOTD caption suitable for Instagram/TikTok. Uses LLM temperature 0.9 so each call produces a distinct result.

| Parameter | Type | Meaning |
|---|---|---|
| `outfit` | `str` | Outfit suggestion string from `suggest_outfit`. Must be non-empty |
| `new_item` | `dict` | Listing dict; `title`, `price`, and `platform` are woven into the caption |

**Returns:** `str` caption mentioning the item name, price, and platform. If `outfit` is empty/whitespace, returns the error string `"Can't create a fit card — the outfit description is missing. Please try your search again."` without calling the LLM.

---

### 4. `compare_price` *(stretch)*

```python
compare_price(item: dict) -> dict
```

**Purpose:** Estimates whether a listing's price is fair by comparing it against all listings in the same category.

| Parameter | Type | Meaning |
|---|---|---|
| `item` | `dict` | Listing dict; uses `category` and `price` |

**Returns:** `dict` with `verdict` (`"great deal"` / `"fair price"` / `"above average"`), `median_price` (float), `percentile` (int, 0–100), `reasoning` (str). Returns `{"verdict": "unknown", "reasoning": "No comparable listings found."}` if no category match.

---

### 5. `get_trends` *(stretch)*

```python
get_trends(size: str | None = None, category: str | None = None) -> dict
```

**Purpose:** Fetches currently trending fashion keywords from public sources and returns them for injection into the outfit prompt.

| Parameter | Type | Meaning |
|---|---|---|
| `size` | `str \| None` | Routes to plus-size subreddits when `1X`/`2X`/`XXL`/`XXXL`; otherwise standard subreddits |
| `category` | `str \| None` | Reserved for future source routing; not currently used |

**Returns:** `dict` with `trends` (list of up to 10 style keywords), `source` (human-readable label), and optionally `error` (str). On total failure returns `{"trends": [], "source": "unavailable"}`.

---

### 6. Style Profile Helpers *(stretch)* — `utils/style_profile.py`

| Function | Signature | Purpose |
|---|---|---|
| `load_profile()` | `-> dict` | Reads `data/style_profile.json`; returns empty skeleton on missing/corrupt file |
| `save_profile(profile)` | `(dict) -> None` | Writes profile to disk with updated `last_updated` timestamp |
| `update_profile(profile, session)` | `(dict, dict) -> dict` | Increments `style_counts` and `color_counts` from the selected listing; updates `preferred_sizes` by category; increments `interaction_count` |
| `top_n(count_dict, n=5)` | `(dict, int) -> list` | Returns top-N keys by frequency; used to cap prompt injection at 5 styles and 5 colors |
| `format_profile_summary(profile)` | `(dict) -> str` | One-line summary for the Gradio profile panel |

---

## Multi-Step Workflow

**Example query:** `"I'm looking for a vintage graphic tee under $30, size M"`

1. **Parse** — regex extracts `description="vintage graphic tee"`, `size="M"`, `max_price=30.0`. Stored in `session["parsed"]`.

2. **`search_listings("vintage graphic tee", "M", 30.0)`** — returns relevance-sorted list. Top result (e.g. `"Faded Nirvana Tee — $22, Depop, Good condition"`) stored as `session["selected_item"]`.

3. **`compare_price(session["selected_item"])`** — returns `{"verdict": "great deal", "percentile": 18, ...}`. Stored in `session["price_comparison"]` and surfaced in the listing panel.

4. **`get_trends(size="M", category="tops")`** — returns `{"trends": ["vintage", "Y2K", "streetwear"], "source": "Reddit r/femalefashionadvice..."}`. Stored in `session["trends"]`.

5. **`suggest_outfit(selected_item, wardrobe, trends=session["trends"], ...)`** — LLM generates outfit combining the tee with wardrobe pieces, weaving in trend context. Result stored as `session["outfit_suggestion"]`.

6. **`create_fit_card(outfit_suggestion, selected_item)`** — LLM generates casual caption at temperature 0.9. Stored as `session["fit_card"]`.

7. **`update_profile(profile, session)`** — increments style/color counts from the selected item for future sessions.

8. **`handle_query()`** maps the session to three Gradio panels: listing + price verdict, outfit suggestion, fit card.

**Error path:** If `search_listings` returns `[]` after all retries, the agent sets `session["error"]` and returns immediately — `suggest_outfit` and `create_fit_card` are never called.

---

## How the Planning Loop Works

`run_agent()` in [agent.py](agent.py) is a sequential conditional chain — each step gates on the success of the prior one:

1. **Parse query** — regex extracts `description`, `size`, `max_price`, and optional `category` hint from the raw query string.

2. **Search with retry fallback** — builds up to 4 filter configurations tried in order:
   - (a) all filters: description + size + max_price + category
   - (b) drop category
   - (c) also drop size
   - (d) also drop max_price
   
   Stops at the first non-empty result. Records what was loosened in `session["retry_note"]`.
   
   **If all 4 return `[]`:** sets `session["error"]` = `"No listings found for '...' even after loosening all filters. Try a different description."` and returns early. `suggest_outfit` is never called.

3. **`compare_price`** — called unconditionally after a result is found; any exception is caught and `session["price_comparison"]` is set to `None`. Non-blocking — the loop always continues.

4. **`get_trends`** — same pattern: called, exception swallowed, `session["trends"]` defaults to empty dict. Non-blocking.

5. **`suggest_outfit`** — called with the selected item, wardrobe, and trends. **If it raises or returns an empty string:** sets `session["error"]` and returns early. `create_fit_card` is never called with an empty suggestion.

6. **`create_fit_card`** — called with the outfit string. **If it raises:** sets `session["error"]` and returns early.

7. **`update_profile`** — persists style preferences to disk. Returns the completed session.

The agent's behavior is demonstrably conditional: running with `"designer ballgown size XXS under $5"` exits after step 2 with `session["fit_card"] == None` and `session["error"]` set, while a valid query flows through all six tools.

---

## State Management

All state lives in a single `session` dict created by `_new_session()` at the start of each call to `run_agent()`. No global variables are used; the dict is passed by reference through the entire call chain and returned to `handle_query()` at the end.

| Key | Type | Set when | Used by |
|---|---|---|---|
| `query` | `str` | Init | Query parser |
| `parsed` | `dict` | After regex parsing | `search_listings` |
| `search_results` | `list[dict]` | After `search_listings` | Branch check |
| `selected_item` | `dict \| None` | After non-empty results confirmed | `compare_price`, `get_trends`, `suggest_outfit`, `create_fit_card` |
| `wardrobe` | `dict` | Init (passed in by caller) | `suggest_outfit` |
| `price_comparison` | `dict \| None` | After `compare_price` | `handle_query` — listing panel |
| `trends` | `dict \| None` | After `get_trends` | `suggest_outfit` (kwarg); `handle_query` — listing panel |
| `outfit_suggestion` | `str \| None` | After `suggest_outfit` | `create_fit_card` |
| `fit_card` | `str \| None` | After `create_fit_card` | Returned to UI |
| `error` | `str \| None` | On any early-termination condition | `handle_query` |
| `retry_note` | `str \| None` | After retry loop | `handle_query` — listing panel |
| `style_profile` | `dict` | Loaded at start; updated after `create_fit_card` succeeds | `suggest_outfit` prompt injection; Gradio profile panel |

`session["selected_item"]` is the same dict object passed into `compare_price`, `suggest_outfit`, and `create_fit_card` — the user never re-enters it. `session["outfit_suggestion"]` is the exact string returned by `suggest_outfit` and passed directly as `outfit` to `create_fit_card`.

---

## Error Handling

| Tool | Failure mode | Agent response |
|---|---|---|
| `search_listings` | Returns `[]` after all retries | `"No listings found for '...' even after loosening all filters. Try a different description."` — session returned early; no further tools called |
| `compare_price` | Any exception | `session["price_comparison"] = None`; price verdict omitted from UI; loop continues |
| `get_trends` | Network error / all sources fail | `session["trends"] = {"trends": [], "source": "unavailable"}`; `suggest_outfit` called without trend context; loop continues |
| `suggest_outfit` | LLM exception or empty return | `"Couldn't generate an outfit suggestion — the styling service is unavailable. Try again in a moment."` — session returned early; `create_fit_card` not called |
| `create_fit_card` | `outfit` is empty/whitespace | Returns `"Can't create a fit card — the outfit description is missing. Please try your search again."` without calling LLM |
| `create_fit_card` | LLM exception | `"Fit card generation failed. Your outfit suggestion is ready — the caption couldn't be created this time."` — session returned early |

**Concrete triggered-failure example — `search_listings` zero results:**

```bash
python -c "from agent import run_agent; from utils.data_loader import get_empty_wardrobe; s = run_agent('designer ballgown size XXS under \$5', get_empty_wardrobe()); print(s['error']); print('fit_card:', s['fit_card'])"
```

Output:
```
No listings found for 'designer ballgown' under $5 in the 'ballgown' category even after loosening all filters. Try a different description.
fit_card: None
```

`session["fit_card"]` is `None` — `suggest_outfit` was never called.

**Concrete triggered-failure example — `create_fit_card` with empty outfit:**

```bash
python -c "from tools import search_listings, create_fit_card; r = search_listings('vintage tee', None, 50); print(create_fit_card('', r[0]))"
```

Output:
```
Can't create a fit card — the outfit description is missing. Please try your search again.
```

No exception raised; the function returns the error string.

---

## Style Profile Memory *(stretch)*

**Storage:** `data/style_profile.json` — written after every successful fit card interaction.

**Stored fields:**

| Field | Type | Description |
|---|---|---|
| `style_counts` | `dict[str, int]` | Frequency map of style tags from selected listings (e.g. `{"vintage": 3, "streetwear": 1}`) |
| `color_counts` | `dict[str, int]` | Frequency map of colors from selected listings |
| `preferred_sizes` | `dict[str, str]` | Most recent size per category (e.g. `{"tops": "M"}`) |
| `interaction_count` | `int` | Total completed interactions |
| `last_updated` | `str` | ISO 8601 timestamp |

**How it influences suggestions:** When a non-empty profile exists, `suggest_outfit` prepends to the LLM prompt: *"User's remembered style profile — preferred styles: vintage, streetwear; preferred colors: black, white. Incorporate these naturally where they fit."* Only the top 5 styles and top 5 colors by frequency are injected to prevent prompt bloat.

**UI:** The Gradio app shows a "Your Style Profile" panel that updates after each query. A "Clear Style Profile" button resets `data/style_profile.json` to an empty state.

**Verification:** Run the app twice with different queries. After the second run, inspect `data/style_profile.json` — `style_counts` and `color_counts` should show accumulated values from both sessions.

---

## Trend Awareness *(stretch)*

**Sources (in priority order):**

1. **Reddit public JSON API** — `GET https://www.reddit.com/r/{subreddit}/top.json?t=week&limit=15`
   - Standard sizes (S, M, L, XL) → `r/femalefashionadvice` + `r/streetwear`
   - Plus sizes (1X, 2X, XXL, XXXL) → `r/PlusSizeFashion` + `r/plussize`
2. **Who What Wear RSS** — fallback if Reddit returns non-200 or no titles
3. **Refinery29 RSS** — fallback if Who What Wear also fails

**Keyword extraction:** Post and article titles are scanned against a curated list of recognized style keywords (`cottagecore`, `quiet luxury`, `gorpcore`, `Y2K`, `grunge`, `streetwear`, `preppy`, `boho`, `minimalist`, `dark academia`, `old money`, `coquette`, `barbiecore`, `normcore`, `techwear`, `vintage`, `retro`, and others). Up to 10 matched keywords returned.

**How it influences suggestions:** When `trends["trends"]` is non-empty, `suggest_outfit` appends to the LLM prompt: *"Current trending styles this week: y2k, quiet luxury. Where relevant, weave one of these trends into your outfit suggestion."*

**Failure handling:** If all sources fail, `get_trends` returns `{"trends": [], "source": "unavailable"}` — never raises. `suggest_outfit` is called without trend context and the interaction completes normally.

---

## Retry Logic with Fallback *(stretch)*

When `search_listings` returns no results, the agent automatically retries up to 3 additional times with progressively loosened constraints:

| Attempt | Filters active |
|---|---|
| 1 | description + size + max_price + category |
| 2 | description + size + max_price (category dropped) |
| 3 | description + size (max_price also dropped) |
| 4 | description only (size and max_price both dropped) |

On the first non-empty result, `session["retry_note"]` records what was loosened (e.g. `"size and price filters removed"`), and this note appears in the listing panel so the user knows their query was adjusted. Only if all four attempts return `[]` does the agent set `session["error"]` and stop.

---

## Spec Reflection

**One way the spec helped:** The tool specs in `planning.md` listed exact parameter names, types, and return field names before any code was written. This made AI-generated implementations verifiable mechanically. If a generated function used `item["style"]` instead of `item["style_tags"]`, that was a clear mismatch against the spec, not a judgment call.

**One divergence and why:** The initial spec described a wardrobe item's style field as `style` (str). The actual `wardrobe_schema.json` in the starter repo uses `style_tags` (list[str]). The implementation was updated to match the schema so that `style_tags` is used throughout `suggest_outfit` and the test suite. The spec was updated in `planning.md` with an implementation note to record the divergence.

---

## AI Usage

**Instance 1 — `search_listings` implementation**

I gave Claude the Tool 1 spec block from `planning.md` (inputs with types, return value with all field names, `_size_matches` logic description) and the `load_listings()` docstring from `utils/data_loader.py`. I asked it to implement `search_listings` in `tools.py` using `load_listings()`.

Before running it, I reviewed: (1) did it apply all three filters? (2) did it score by keyword overlap across `title` + `description` + `style_tags`? (3) did it return `[]` without raising on zero results?

What I changed: the generated code used exact string matching for size. I added the slash-range splitting (`S/M` → `["S", "M"]`) and bottoms token splitting (`W30 L30` → `["W30", "L30"]`) after inspecting the actual data and seeing those patterns in the listings.

**Instance 2 — Planning loop / `run_agent` implementation**

I gave Claude the Planning Loop section, State Management section, and Architecture diagram from `planning.md`, plus the existing `_new_session()` and `run_agent()` stub from `agent.py`. I asked it to implement `run_agent()` following the conditional chain exactly.

Before running it, I verified: (1) did it branch on `search_results == []` before calling `suggest_outfit`? (2) did it use the exact session key names from `_new_session()`? (3) did it avoid calling all three tools unconditionally?

What I changed: the generated code ran a single `search_listings` call with no retry. I replaced that with the retry loop (four progressively looser filter configurations, stopping on the first non-empty result) and added `session["retry_note"]` tracking manually.
