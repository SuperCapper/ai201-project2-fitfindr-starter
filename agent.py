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
from tools import search_listings, suggest_outfit, create_fit_card


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
    # Step 1: Initialize the session
    session = _new_session(query, wardrobe)
    
    # Step 2: Parse the user's query to extract description, size, and max_price
    # Use regex for parsing
    description = query.strip()
    size = None
    max_price = None
    
    # Extract max_price (look for "$" followed by a number)
    price_match = re.search(r'\$(\d+(?:\.\d+)?)', query)
    if price_match:
        max_price = float(price_match.group(1))
        # Remove the price part from description
        description = re.sub(r'\$(\d+(?:\.\d+)?)', '', description).strip()
    
    # Extract size (look for "size" followed by a word or pattern like "M", "L", "XL", "S/M", "W30 L30")
    size_match = re.search(r'size\s*[:]?\s*([\w/]+(?:\s+[\w/]+)*)', query, re.IGNORECASE)
    if size_match:
        size = size_match.group(1).strip()
        # Remove the size part from description
        description = re.sub(r'size\s*[:]?\s*[\w/]+(?:\s+[\w/]+)*', '', description, flags=re.IGNORECASE).strip()
    
    # If description is empty after stripping, set a default error
    if not description:
        session["error"] = "Please describe what you're looking for (e.g., 'vintage tee under $30')."
        return session
    
    # Store parsed parameters in session
    session["parsed"] = {
        "description": description,
        "size": size,
        "max_price": max_price
    }
    
    # Step 3: Call search_listings() with the parsed parameters
    search_results = search_listings(
        description=description,
        size=size,
        max_price=max_price
    )
    session["search_results"] = search_results
    
    # If no results, set error and return early
    if not search_results:
        session["error"] = "No listings found matching your criteria. Try adjusting your search."
        return session
    
    # Step 4: Select the top result
    session["selected_item"] = search_results[0]
    
    # Step 5: Call suggest_outfit() with the selected item and wardrobe
    outfit_suggestion = suggest_outfit(
        new_item=session["selected_item"],
        wardrobe=wardrobe
    )
    session["outfit_suggestion"] = outfit_suggestion
    
    # Check if suggest_outfit returned an error string
    if "Error:" in outfit_suggestion or "Sorry, I couldn't generate" in outfit_suggestion:
        session["error"] = "Could not generate an outfit suggestion. Please try again."
        return session
    
    # Step 6: Call create_fit_card() with the outfit suggestion and selected item
    fit_card = create_fit_card(
        outfit=outfit_suggestion,
        new_item=session["selected_item"]
    )
    session["fit_card"] = fit_card
    
    # Check if create_fit_card returned an error string
    if "Could not create a fit card" in fit_card or "Could not generate a fit card" in fit_card:
        session["error"] = "Could not create a fit card."
        return session
    
    # Step 7: Return the session (error is None on success)
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import io
    # Set UTF-8 encoding for console output to handle emojis
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
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
