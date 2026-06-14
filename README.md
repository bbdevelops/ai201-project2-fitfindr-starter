# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Trend Awareness Tool

`get_trends(size, category)` fetches currently trending fashion styles from public sources and injects them into the outfit suggestion.

**Data sources (in priority order):**

1. **Reddit JSON API** — pulls the top posts from the past week via `https://www.reddit.com/r/{subreddit}/top.json?t=week&limit=15`. Subreddit selection adapts to the user's size:
   - Standard sizes → `r/femalefashionadvice` + `r/streetwear`
   - Plus sizes (1X, 2X, XXL, etc.) → `r/PlusSizeFashion` + `r/plussize`
2. **Fashion publication RSS feeds** (fallback if Reddit is unavailable) — `Who What Wear` and `Refinery29` public RSS feeds.

**Keyword extraction:** Post/article titles are scanned against a curated list of recognized style keywords (e.g., `cottagecore`, `quiet luxury`, `Y2K`, `gorpcore`). Up to 10 matched keywords are returned.

**Integration:** Trend keywords are appended to the `suggest_outfit` LLM prompt so the outfit recommendation explicitly references what's currently popular. Example prompt addition:

> *Current trending styles this week: y2k, quiet luxury. Where relevant, weave one of these trends into your outfit suggestion.*

**Failure handling:** If both Reddit and RSS feeds fail (network issues, rate limits), `get_trends` returns `{"trends": [], "source": "unavailable"}` and the agent continues normally — the outfit suggestion is generated without trend context rather than failing the interaction.

## Style Profile Memory (Stretch Feature)

FitFindr remembers your style preferences across sessions so outfit suggestions improve over time without you re-entering your tastes.

**Storage:** `data/style_profile.json` — a single JSON file written to disk after every successful interaction.

**What is stored:**

| Field | Type | Description |
|-------|------|-------------|
| `style_counts` | dict[str, int] | Frequency map of style tags from selected listings (e.g., `{"vintage": 3, "streetwear": 1}`) |
| `color_counts` | dict[str, int] | Frequency map of colors from selected listings (e.g., `{"black": 4, "white": 2}`) |
| `preferred_sizes` | dict[str, str] | Most recent size per category (e.g., `{"tops": "M", "shoes": "9"}`) |
| `interaction_count` | int | Total number of completed interactions |
| `last_updated` | str | ISO 8601 timestamp of last write |

**How preferences are accumulated:** After every successful fit card interaction, `update_profile()` increments the count for each `style_tag` and `color` on the selected listing, and stores the query's parsed size under the item's category. Counts are never capped in storage — they grow naturally across sessions.

**How the top-5 cap works:** When building the LLM prompt for `suggest_outfit`, only the **top 5** style tags and top 5 colors by frequency are injected. This prevents prompt bloat after many sessions while keeping the most consistently preferred tags front-and-center.

**How it influences suggestions:** When a non-empty profile exists, `suggest_outfit` prepends this to its Groq prompt:

> *User's remembered style profile — preferred styles: vintage, streetwear; preferred colors: black, white. Incorporate these naturally where they fit.*

**UI controls:** The Gradio app shows a "Your Style Profile" panel that updates after each query. A "Clear Style Profile" button resets the file to an empty state.

**Verification:** Run the app twice with different queries and inspect `data/style_profile.json` — counts should accumulate across runs. The second run's outfit suggestion will reflect the top tags from the first.

---

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.
