# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock listings dataset (from `listings.json`) for items that match a user's description, size, and price constraints. Returns a list of matching listing dicts sorted by relevance (best match first). Does not call the LLM — it uses keyword overlap scoring.

**Input parameters:**
- `description` (str): Keywords the user typed (e.g., "vintage graphic tee"). Used for relevance scoring.
- `size` (str | None): Optional size string (e.g., "M", "W30 L30"). If provided, case‑insensitive partial matching against the listing's `size` field.
- `max_price` (float | None): Optional maximum price (inclusive). If provided, filters by `price <= max_price`.

**What it returns:**
A list of matching listing dicts. Each dict contains exactly the fields from `listings.json`: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. The list is sorted by relevance score (highest first). Returns an empty list if no matches.

**What happens if it fails or returns nothing:**
If no matches are found, the planning loop checks for an empty list, sets `session["error"]` to `"No listings found matching your criteria. Try adjusting your search."`, and returns early without calling `suggest_outfit` or `create_fit_card`.

---

### Tool 2: suggest_outfit

**What it does:**
Given a newly found thrifted item and the user's current wardrobe, generates 1–2 specific outfit ideas by calling the Groq LLM. If the wardrobe is empty, it instead offers general styling advice.

**Input parameters:**
- `new_item` (dict): A single listing dict (the item the user is considering buying). Must contain at least `title`, `category`, `style_tags`, and `colors`.
- `wardrobe` (dict): A wardrobe dict with an `items` key containing a list of wardrobe item dicts (each with `name`, `category`, `colors`, `style_tags`, `notes`).

**What it returns:**
A non‑empty string containing the outfit suggestions. Example: *"Pair the vintage tour tee with your baggy straight-leg jeans and chunky white sneakers. Add a black denim jacket for layering."* If the wardrobe is empty, the string might be: *"This vintage tee looks great with baggy denim, combat boots, and an oversized flannel — perfect for a grunge vibe."*

**What happens if it fails or returns nothing:**
If the client fails to initialize, the LLM call fails (e.g., API error), or the LLM returns an empty/whitespace string, the tool raises `ToolError`. The planning loop catches it, sets `session["error"] = "Could not generate an outfit suggestion. Please try again."`, then returns early. It does not proceed to `create_fit_card`.

---

### Tool 3: create_fit_card

**What it does:**
Generates a short (2–4 sentence), shareable outfit caption (like an Instagram/TikTok post) by calling the Groq LLM with a high temperature. The caption mentions the item name, price, and platform once, and captures the outfit vibe authentically.

**Input parameters:**
- `outfit` (str): The outfit suggestion string returned by `suggest_outfit`.
- `new_item` (dict): The listing dict for the thrifted item (needed for price, platform, title).

**What it returns:**
A string of 2–4 sentences, never empty. Example: *"Just snagged this faded tour tee on Depop for $24 — the perfect grunge layer. Wearing it with my go-to baggy jeans and chunky sneakers. 💥 #thriftfind #vintagefashion"*

**What happens if it fails or returns nothing:**
If `outfit` is empty or whitespace, the client fails to initialize, or the LLM call fails, the tool raises `ToolError` and the planning loop sets `session["error"] = "Could not create a fit card."` and returns early. If the LLM instead returns an empty string, the tool treats it as non-fatal and returns a fallback caption: *"Just snagged this piece — can't wait to style it with my wardrobe!"*

---

### Additional Tools (if any)

None beyond the three required.

---

## Planning Loop

**How does your agent decide which tool to call next?**

The planning loop follows a strict sequence of three steps, with conditional branching at each step. After initializing the session, the loop does the following:

1. **Parse the user query** into `description`, `size`, and `max_price`.  
   - If parsing fails (e.g., no description), set `session["error"] = "Please describe what you're looking for (e.g., 'vintage tee under $30')."` and return.

2. **Call `search_listings(description, size, max_price)`**.  
   - If the returned list is empty → set `session["error"] = "No listings found matching your criteria. Try adjusting your search."` → **return** (skip further tools).  
   - If the list has at least one item → select `session["selected_item"] = results[0]` (the top result).  

3. **Call `suggest_outfit(selected_item, wardrobe)`**.  
   - If `suggest_outfit` raises `ToolError` (client/LLM failure or empty completion) → set `session["error"] = "Could not generate an outfit suggestion. Please try again."` → **return**.  
   - Otherwise, store the string in `session["outfit_suggestion"]`.

4. **Call `create_fit_card(outfit_suggestion, selected_item)`**.  
   - If `create_fit_card` raises `ToolError` (missing outfit, client/LLM failure) → set `session["error"] = "Could not create a fit card."` → **return**.  
   - Otherwise, store the string in `session["fit_card"]` (an empty LLM completion yields a non-fatal fallback caption, not an error).

5. **Return the session dict** (with `error = None`).

The loop never calls a tool if a previous tool failed or returned no usable output. The session dict contains all intermediate results, and each tool's output is passed as input to the next tool.

---

## State Management

**How does information from one tool get passed to the next?**

All state is stored in a single Python dict called the **session**. The session is created at the start of `run_agent()` and contains the following keys:

- `query` (str): original user query
- `parsed` (dict): extracted `description`, `size`, `max_price`
- `search_results` (list[dict]): full list of matching listings from `search_listings`
- `selected_item` (dict): the top result (used as input to `suggest_outfit`)
- `wardrobe` (dict): the user's wardrobe (passed in from the interface)
- `outfit_suggestion` (str): output of `suggest_outfit`
- `fit_card` (str): output of `create_fit_card`
- `error` (str | None): `None` if successful, otherwise an error message

The planning loop reads and writes to this dict. Each tool receives the necessary fields directly as arguments (e.g., `suggest_outfit(new_item, wardrobe)`), not the whole session — this keeps tools testable in isolation. The loop is responsible for extracting the relevant session fields before each tool call and storing the results back into the session.

Example flow:  
`session["selected_item"] = session["search_results"][0]`  
`outfit = suggest_outfit(session["selected_item"], session["wardrobe"])`  
`session["outfit_suggestion"] = outfit`

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

Tools signal failure structurally by raising `ToolError` (defined in `tools.py`) rather than returning an error string; the planning loop catches it to set `session["error"]` and return early.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Set `session["error"] = "No listings found matching your criteria. Try adjusting your search."` and return early (do not call subsequent tools). |
| suggest_outfit | Wardrobe is empty | The tool calls the LLM with a prompt that asks for general styling advice instead of specific wardrobe pairings. The agent does **not** treat this as an error — it returns a valid styling string and continues to `create_fit_card`. |
| suggest_outfit | Client init fails, LLM call fails (e.g., network error, invalid API key), or the LLM returns an empty completion | The tool raises `ToolError`. The loop catches it, sets `session["error"] = "Could not generate an outfit suggestion. Please try again."`, and returns early. |
| create_fit_card | `outfit` input is missing/empty, client init fails, or the LLM call fails | The tool raises `ToolError`. The loop catches it, sets `session["error"] = "Could not create a fit card."`, and returns early. |
| create_fit_card | LLM returns an empty completion | Non-fatal. The tool returns a generic fallback caption (`"Just snagged this piece — can't wait to style it with my wardrobe!"`) and the loop continues with `error = None`. |

---

## Architecture

Below is an ASCII art diagram of the agent's control and data flow.

```
┌─────────────────────┐
│ User query          │
│ + wardrobe          │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│ Planning Loop                                            │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 1. Parse query → description, size,              │  │
│  │    max_price                                     │  │
│  │    If parse fails → return error                 │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 2. search_listings(description,                   │  │
│  │    size, max_price)                              │  │
│  │    results = [...]                               │  │
│  │    if results == [] →                            │  │
│  │       error → return early                       │  │
│  │    else: selected_item = results[0]              │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 3. suggest_outfit(selected_item,                  │  │
│  │    wardrobe)                                     │  │
│  │    if fails → error → return early               │  │
│  │    else: outfit_suggestion = result              │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 4. create_fit_card(outfit_suggestion,             │  │
│  │    selected_item)                                │  │
│  │    if fails → error → return early               │  │
│  │    else: fit_card = result                       │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 5. Return session (with error=None)              │  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
└──────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────┐
│ Session dict         │
│ (to Gradio)          │
└──────────────────────┘
```

Data flow:  
- `search_results` → `selected_item` → `suggest_outfit` → `outfit_suggestion` → `create_fit_card` → `fit_card`  
- Error paths return the session early without proceeding to downstream tools.

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

I'll use Amazon Q Developer to implement each tool individually. For each tool:
- Input: The complete tool specification from the Tools section (what it does, input parameters, return value, failure modes)
- Expected output: A working function in `tools.py` that matches the spec exactly
- Verification: Write unit tests for each tool using pytest, testing both success cases and all documented failure modes

Tool 1 (search_listings): Give Q the Tool 1 spec, the `listings.json` schema, and the `load_listings()` function signature. Test with 3 queries: (1) exact match, (2) partial match with filters, (3) no matches.

Tool 2 (suggest_outfit): Give Q the Tool 2 spec, the wardrobe schema, and example prompts for LLM calls. Test with: (1) full wardrobe, (2) empty wardrobe, (3) mock API error.

Tool 3 (create_fit_card): Give Q the Tool 3 spec and example output format. Test with: (1) valid outfit input, (2) empty outfit string, (3) mock API error with fallback.

**Milestone 4 — Planning loop and state management:**

I'll use Amazon Q Developer to implement the planning loop in `agent.py`. 
- Input: The Planning Loop, State Management, and Error Handling sections, plus all three tool signatures
- Expected output: A `run_agent(query, wardrobe)` function that returns a session dict
- Verification: Write integration tests that run the full agent with various inputs:
  1. Happy path (successful search → outfit → fit card)
  2. No search results (early return with error)
  3. LLM failure in suggest_outfit (early return with error)
  4. Empty wardrobe (successful flow with general advice)

I'll verify each step by checking that the session dict contains the correct keys and values, and that errors stop execution at the right point.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**What FitFindr needs to do (2–3 sentences)**
FitFindr helps a user find a secondhand item based on a natural language query (e.g., "vintage graphic tee under $30"). It first searches the mock listings dataset using search_listings to return matching items. If a match is found, it uses suggest_outfit to generate styling ideas by combining the found item with the user's existing wardrobe, then produces a shareable caption via create_fit_card. If any tool fails (e.g., no results, empty wardrobe, or missing data), the agent returns a clear error message and stops early — it does not proceed with subsequent tools.

**Example user query:**
"I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1: Parse the query**
The agent extracts description = "vintage graphic tee", max_price = 30.0, and size = None (no size specified). No size filter is applied.

**Step 2: Call search_listings(description="vintage graphic tee", size=None, max_price=30.0)**
The tool loads all listings, filters by price ≤ 30, and scores each by keyword overlap with "vintage", "graphic", "tee". It returns a list of matching listings sorted by relevance (e.g., items like lst_002, lst_006, lst_033). The top result is selected (e.g., lst_006 – "Graphic Tee — 2003 Tour Bootleg Style", price $24, size L).

**Step 3: Call suggest_outfit(new_item=lst_006, wardrobe=user_wardrobe)**
The user's wardrobe contains baggy jeans and chunky sneakers (from the example wardrobe). The tool calls the LLM with a prompt asking for 1–2 outfit ideas using the new tee, the baggy jeans, and the sneakers. It returns a string like:
"Pair the vintage tour tee with your baggy straight-leg jeans and chunky white sneakers. Add a black denim jacket for layering — perfect for a casual day out."

**Step 4: Call create_fit_card(outfit=outfit_string, new_item=lst_006)**
The tool prompts the LLM to generate a short, shareable caption. Example output:
*"Just snagged this faded tour tee on Depop for $24 — the perfect grunge layer. Wearing it with my go-to baggy jeans and chunky sneakers. 💥 #thriftfind #vintagefashion"*

**Final output to user:**
The agent returns a session dict containing:
- `selected_item`: the full listing dict for lst_006
- `outfit_suggestion`: the styling text
- `fit_card`: the caption text
- `error`: None

The Gradio interface displays the top listing, the outfit idea, and the fit card in their respective panels.
