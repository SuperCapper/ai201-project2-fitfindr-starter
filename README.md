# FitFindr — AI-Powered Secondhand Stylist

FitFindr is a multi-tool AI agent that helps users discover secondhand fashion pieces and visualize how to style them with their existing wardrobe. Given a natural language query (e.g., *"vintage graphic tee under $30"*), the agent searches a mock dataset of thrift listings, suggests outfits using the user's wardrobe (or general styling advice when the wardrobe is empty), and generates a shareable social-media caption.

---

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## Running FitFindr

Launch the Gradio app and open the printed local URL (e.g. http://127.0.0.1:7860):
```bash
python app.py
```

Or drive the agent directly:
```python
from agent import run_agent
from utils.data_loader import get_example_wardrobe

session = run_agent("vintage graphic tee under $30", get_example_wardrobe())
print(session["fit_card"])
print(session["error"])   # None on success
```

---

## Tools Inventory

### 1. `search_listings(description, size, max_price)`

| | |
|--|--|
| **Purpose** | Finds secondhand items matching the user's description, size, and price constraints. Uses keyword-overlap scoring (no LLM). |
| **Inputs** | `description` (str) – keywords from the user query, e.g., `"vintage graphic tee"`<br>`size` (str \| None) – optional size filter (case-insensitive partial match)<br>`max_price` (float \| None) – optional maximum price, inclusive |
| **Outputs** | List of matching listing dicts, sorted by relevance (highest score first). Returns `[]` if no matches — **never raises**. |

### 2. `suggest_outfit(new_item, wardrobe)`

| | |
|--|--|
| **Purpose** | Generates 1–2 outfit ideas using the newly found item and the user's existing wardrobe. If the wardrobe is empty, offers general styling advice. |
| **Inputs** | `new_item` (dict) – the listing the user is considering buying (must contain `title`, `category`, `style_tags`, `colors`)<br>`wardrobe` (dict) – user's wardrobe with an `items` list |
| **Outputs** | Non-empty string with outfit suggestions or styling advice. On client/LLM failure or an empty completion, **raises `ToolError`**. |

### 3. `create_fit_card(outfit, new_item)`

| | |
|--|--|
| **Purpose** | Creates a short, shareable Instagram-style caption for the outfit. |
| **Inputs** | `outfit` (str) – the outfit suggestion from `suggest_outfit`<br>`new_item` (dict) – the original listing |
| **Outputs** | 2–4 sentence caption. **Raises `ToolError`** if `outfit` is empty/missing or the LLM call fails; an empty LLM completion returns a fallback caption. |

> **Failure contract:** the two LLM-backed tools signal failure by **raising `ToolError`** (defined in `tools.py`) rather than returning error strings. The planning loop catches it and records a user-facing message in `session["error"]`. `search_listings` is the exception — it returns `[]` on no match.

---

## Planning Loop

The agent follows a linear, conditional workflow:

1. **Parse query** → extract `description`, `size`, and `max_price` using regex.
2. **Call `search_listings`** → if no results, set `session["error"]` to a `"No listings found. …"` message with a context-specific suggestion (drop the size filter, raise the price limit, or broaden keywords) and **return early**.
3. **Select top result** → store as `session["selected_item"]`.
4. **Call `suggest_outfit`** → if it raises `ToolError`, set `session["error"] = "Could not generate an outfit suggestion. Please try again."` and **return early**.
5. **Call `create_fit_card`** → if it raises `ToolError`, set `session["error"] = "Could not create a fit card."` and **return early**.
6. **Return session** → success case: `error = None`.

The loop **never** calls a downstream tool if a previous step failed or returned no usable output, so the agent fails fast and communicates clearly. An empty wardrobe is **not** a failure — `suggest_outfit` returns general styling advice and the loop continues.

---

## State Management

All state is stored in a Python **session dict** created at the start of each interaction:

```python
session = {
    "query": str,                # original user query
    "parsed": dict,              # extracted description, size, max_price
    "search_results": list,      # full list from search_listings
    "selected_item": dict,       # top result (input to suggest_outfit)
    "wardrobe": dict,            # user's wardrobe (passed from app)
    "outfit_suggestion": str,    # output of suggest_outfit
    "fit_card": str,             # output of create_fit_card
    "error": str | None          # None if successful
}
```

Each tool receives only the fields it needs (not the whole session), which keeps the tools testable in isolation. The planning loop reads inputs from the session before each call and writes results back.

---

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format the agent uses to represent a user's existing wardrobe:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items for testing
- `empty_wardrobe`: a starting template for a new user

```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

---

## Testing

Run the automated suite:
```bash
python -m pytest
```

31 tests cover the three tools, the `run_agent` planning loop (including the `ToolError` paths and query parsing), and the Gradio handler. See [`TESTING.md`](TESTING.md) for the full record, including manual state-flow verification (`verify_state.py`).

## Demo Video

A screen recording (`Screen Recording 2026-06-14 204551.mp4`) is **submitted separately** — it is not committed to this repository (large binary). It demonstrates:

- The full FitFindr Gradio app running end to end (search → outfit suggestion → fit card).
- A **failure mode**: when the outfit step yields nothing, `create_fit_card` raises a `ToolError`, the planning loop catches it, and the app shows a clear error (`⚠️ Could not create a fit card.`) instead of crashing.

---

## Project Structure

```
ai201-project2-fitfindr-starter/
├── agent.py                  # run_agent() planning loop
├── app.py                    # Gradio interface (handle_query)
├── tools.py                  # search_listings, suggest_outfit, create_fit_card, ToolError
├── planning.md               # design doc (tools, loop, state, error handling)
├── TESTING.md                # testing documentation
├── tests/                    # pytest suite (test_tools, test_agent, test_app)
├── data/                     # listings.json, wardrobe_schema.json
├── utils/data_loader.py      # data loading helpers
└── requirements.txt          # Python dependencies
```
