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
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): ...
- `size` (str): ...
- `max_price` (float): ...

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): ...
- `wardrobe` (dict): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->

---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): ...

**What it returns:**
<!-- Describe the return value -->

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | |
| suggest_outfit | Wardrobe is empty | |
| create_fit_card | Outfit input is missing or incomplete | |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

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

**Milestone 4 — Planning loop and state management:**

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
The agent returns the found item (lst_006), the outfit suggestion, and the shareable fit card caption to display in the UI.
