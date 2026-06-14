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

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.
