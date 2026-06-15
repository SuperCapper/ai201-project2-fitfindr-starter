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

## Error Handling

Each tool has a defined failure mode, and the planning loop ([`agent.py`](agent.py)) decides what the user sees:

| Tool | Failure mode | Agent response |
|------|--------------|----------------|
| `search_listings` | No listings match the query | Returns `[]` (never raises). The loop sets `session["error"]` to a context-specific message — e.g. `"No listings found. Try a different size (e.g., remove the 'XXS' filter)."` — and returns early without calling the other tools. |
| `suggest_outfit` | Client init fails, LLM call fails, or empty completion | Raises `ToolError`. The loop catches it, sets `session["error"] = "Could not generate an outfit suggestion. Please try again."`, and returns early (never calls `create_fit_card`). An **empty wardrobe is not a failure** — the tool returns general styling advice. |
| `create_fit_card` | Missing/empty outfit, client init fails, or LLM call fails | Raises `ToolError`. The loop catches it and sets `session["error"] = "Could not create a fit card."`. An empty LLM completion is non-fatal — the tool returns a fallback caption. |

**Concrete example from testing.** Feeding an empty outfit into `create_fit_card` raises `ToolError`, which the loop converts into a user-facing error instead of crashing:

```python
>>> from tools import create_fit_card
>>> create_fit_card("", item)
ToolError: Cannot create a fit card: the outfit suggestion was missing.
```

In the running app this surfaces as `⚠️ Could not create a fit card.` in the first panel (covered by `tests/test_tools.py::test_create_fit_card_empty_outfit` and shown in the demo video). The "downstream tools are never called when search is empty" early-return is proven by `verify_state.py` and `tests/test_agent.py::test_run_agent_no_results`, which use mock spies to assert a call count of 0.

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

## Spec Reflection

**Where the spec helped.** Writing `planning.md` first — the tool I/O contracts, the numbered planning loop, and the Error Handling table — made the implementation largely transcription. Defining each tool's inputs/outputs and the session keys up front kept the tools decoupled and made the loop's control flow obvious before any code was written.

**Where the implementation diverged (and why).** The original spec had the tools **return error-message strings** on failure (and the Error Handling table said "catch exception"). That forced the loop to detect failures by substring-matching prose, which was brittle and missed cases — a `create_fit_card` client-init error slipped through as a "successful" caption. I diverged to having `suggest_outfit`/`create_fit_card` **raise a `ToolError`** that the loop catches: structural, exhaustive failure detection. `search_listings` still returns `[]` (an empty result is normal, not an error). `planning.md` and `TESTING.md` were updated to match the new contract.

---

## AI Usage Transparency

I used **Claude** (Anthropic's coding assistant) as a pair-programmer. Specific instances:

1. **Implementing the planning loop.** I gave Claude the Planning Loop and State Management sections of `planning.md` and asked it to implement `run_agent()`. *Reviewed / overrode:* its first version detected tool failures by substring-matching returned error strings (`"Error:" in result`). I flagged this as fragile — it silently passed a `create_fit_card` client-init failure downstream — and directed a refactor so the tools raise `ToolError` and the loop catches it, then had it reconcile the tests, `planning.md`, and `TESTING.md` to the new contract.

2. **Fixing the query parser.** Claude's initial size-extraction regex over-captured trailing words (`"size M cotton tee"` → `"M cotton tee"`), which then failed the size filter. *Revised:* I had it restrict the pattern to size-shaped tokens so it captures `"M"` (and `"W30 L30"`) without swallowing surrounding prose, and add tests for those cases.

3. **Designing the no-results message.** I directed Claude to make the no-results error context-specific (suggest dropping the size filter, raising the price, or broadening keywords). *Reviewed / overrode:* I required keeping the stable `"No listings found"` prefix and the raise-based design — declining a suggested alternative to revert `create_fit_card` to returning a string — and had it propagate the change through the tests and docs.

In each case I reviewed the generated code against `planning.md`, ran it (plus the `pytest` suite and `verify_state.py`) to confirm behavior, and revised the parts that didn't match the spec.

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
