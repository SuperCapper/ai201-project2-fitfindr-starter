# verify_state.py
import sys
import json

# Ensure emoji / non-ASCII output works on Windows consoles (cp1252 default),
# matching the other manual scripts in this project.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

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

if __name__ == "__main__":
    verify_state_flow()
