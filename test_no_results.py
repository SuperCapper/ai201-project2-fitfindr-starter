# test_no_results.py
import sys

# Ensure emoji output works on Windows consoles (cp1252 default).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from agent import run_agent
from utils.data_loader import get_example_wardrobe

# Run with a query that returns no results
session = run_agent(
    query="designer ballgown size XXS under $5",
    wardrobe=get_example_wardrobe()
)

print("=== No-Results Path Verification ===\n")
print(f"session['error']: {session['error']}")
print(f"session['search_results']: {session['search_results']}")
print(f"session['selected_item']: {session['selected_item']}")
print(f"session['outfit_suggestion']: {session['outfit_suggestion']}")
print(f"session['fit_card']: {session['fit_card']}")

# Confirm that the later tools were not called
if session['selected_item'] is None:
    print("\n✅ selected_item is None — suggest_outfit was NOT called")
else:
    print("\n⚠️ selected_item is not None — suggest_outfit was called")

if session['outfit_suggestion'] is None:
    print("✅ outfit_suggestion is None — suggest_outfit was NOT called")
else:
    print("⚠️ outfit_suggestion is not None — suggest_outfit was called")

if session['fit_card'] is None:
    print("✅ fit_card is None — create_fit_card was NOT called")
else:
    print("⚠️ fit_card is not None — create_fit_card was called")
