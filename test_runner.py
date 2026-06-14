import sys
import io

# Set UTF-8 encoding for console output to handle emojis
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe

print("\n=== Testing Tool 1: search_listings ===")
results = search_listings("vintage graphic tee", size="L", max_price=30)
print(f"Found {len(results)} results:")
for i, item in enumerate(results[:2], 1):
    print(f"{i}. {item['title']} - ${item['price']} ({item['platform']})")

print("\n=== Testing Tool 2: suggest_outfit (empty wardrobe) ===")
wardrobe = {"items": []}
outfit_empty = suggest_outfit(results[0], wardrobe)
print(outfit_empty)

print("\n=== Testing Tool 2: suggest_outfit (with wardrobe) ===")
outfit = suggest_outfit(results[0], get_example_wardrobe())
print(outfit)

print("\n=== Testing Tool 3: create_fit_card ===")
fit_card = create_fit_card(outfit, results[0])
print(fit_card)
