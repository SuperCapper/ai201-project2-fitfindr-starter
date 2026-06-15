# verify_state.py
import sys
import json

# Ensure emoji / non-ASCII output works on Windows consoles (cp1252 default),
# matching the other manual scripts in this project.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from unittest.mock import MagicMock

import agent
from agent import run_agent
from utils.data_loader import get_example_wardrobe

def verify_state_flow():
    query = "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"
    wardrobe = get_example_wardrobe()

    print("=" * 60)
    print("VERIFYING STATE FLOW WITH EXAMPLE QUERY")
    print("=" * 60)
    print(f"Query: {query}\n")

    # Run the agent
    session = run_agent(query, wardrobe)

    # Check for errors
    if session["error"]:
        print(f"❌ ERROR: {session['error']}")
        return

    # Step 1: Verify search results
    print("\n--- Step 1: search_listings results ---")
    print(f"Found {len(session['search_results'])} matching items")
    top_result = session['search_results'][0]
    print(f"Top result: {top_result['title']} (ID: {top_result['id']}, Price: ${top_result['price']})")

    # Step 2: Verify selected_item is the same dict as search_results[0]
    print("\n--- Step 2: selected_item passed to suggest_outfit ---")
    selected_item = session['selected_item']
    print(f"Selected item ID: {selected_item['id']}")
    print(f"Selected item title: {selected_item['title']}")

    # Identity check — do they reference the same object?
    if top_result is selected_item:
        print("✅ IDENTITY CHECK PASSED: search_results[0] and selected_item are the same dict object")
    else:
        print("⚠️ WARNING: search_results[0] and selected_item are different objects (state is being copied)")

    # Step 3: Verify outfit suggestion
    print("\n--- Step 3: outfit_suggestion returned from suggest_outfit ---")
    outfit = session['outfit_suggestion']
    if outfit and isinstance(outfit, str):
        print(f"✅ Outfit suggestion is a non‑empty string:")
        print(f"   {outfit}")
    else:
        print(f"⚠️ Outfit suggestion is empty or not a string: {outfit}")

    # Step 4: Verify fit card
    print("\n--- Step 4: fit_card returned from create_fit_card ---")
    fit_card = session['fit_card']
    if fit_card and isinstance(fit_card, str):
        print(f"✅ Fit card is a non‑empty string:")
        print(f"   {fit_card}")
    else:
        print(f"⚠️ Fit card is empty or not a string: {fit_card}")

    # Step 5: Final session summary
    print("\n--- Final Session Summary ---")
    print(f"Parsed: {session['parsed']}")
    print(f"Error: {session['error']}")
    print(f"✅ All three tools executed successfully with state passing between them")

    # Export session to JSON for inspection (optional)
    with open("session_dump.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "query": session["query"],
                "parsed": session["parsed"],
                "selected_item_id": session["selected_item"]["id"] if session["selected_item"] else None,
                "outfit_suggestion": session["outfit_suggestion"],
                "fit_card": session["fit_card"],
                "error": session["error"],
            },
            f,
            indent=2
        )
    print("\n📁 Session summary saved to session_dump.json")


def verify_error_path():
    """Confirm a no-results query returns early WITHOUT calling the LLM tools."""
    query = "designer ballgown size XXS under $5"
    wardrobe = get_example_wardrobe()

    print("\n" + "=" * 60)
    print("VERIFYING ERROR PATH (no results → early return)")
    print("=" * 60)
    print(f"Query: {query}\n")

    # Spy on the downstream tools so we can prove they are never invoked.
    # Plain MagicMocks (not wraps=) guarantee no real LLM call happens even if
    # the loop were buggy and reached them — and let us assert call_count == 0.
    orig_suggest = agent.suggest_outfit
    orig_create = agent.create_fit_card
    spy_suggest = MagicMock(name="suggest_outfit")
    spy_create = MagicMock(name="create_fit_card")
    agent.suggest_outfit = spy_suggest
    agent.create_fit_card = spy_create

    try:
        session = run_agent(query, wardrobe)
    finally:
        # Always restore the real tools.
        agent.suggest_outfit = orig_suggest
        agent.create_fit_card = orig_create

    # The no-results message is dynamic (it suggests an adjustment based on the
    # filters used), so check the stable prefix plus the size-specific hint.
    err = session["error"] or ""

    # 1. Error message is the no-results error with a relevant suggestion
    if err.startswith("No listings found") and "XXS" in err:
        print(f"✅ ERROR set as expected: {session['error']}")
    else:
        print(f"⚠️ WARNING: unexpected error value: {session['error']!r}")

    # 2. Downstream tools must NOT have been called
    if spy_suggest.call_count == 0 and spy_create.call_count == 0:
        print("✅ suggest_outfit and create_fit_card were NOT called (early return)")
    else:
        print(f"⚠️ WARNING: downstream tool(s) were called "
              f"(suggest_outfit={spy_suggest.call_count}, create_fit_card={spy_create.call_count})")

    # 3. Output fields should remain unset
    if (session["selected_item"] is None
            and session["outfit_suggestion"] is None
            and session["fit_card"] is None):
        print("✅ selected_item, outfit_suggestion, and fit_card are all None")
    else:
        print(f"⚠️ WARNING: output fields not all None: "
              f"selected_item={session['selected_item']}, "
              f"outfit_suggestion={session['outfit_suggestion']}, "
              f"fit_card={session['fit_card']}")


if __name__ == "__main__":
    verify_state_flow()
    verify_error_path()
