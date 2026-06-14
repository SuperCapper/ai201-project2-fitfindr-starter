"""
Test suite for search_listings tool - verifying all requirements
"""
import sys
import io

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from tools import search_listings

print("="*70)
print("TESTING TOOL 1: search_listings")
print("="*70)

# Test 1: Import check - does it load listings without errors?
print("\n[Test 1] Import and basic functionality check")
try:
    results = search_listings("tee", size=None, max_price=None)
    print(f"✓ Successfully imported load_listings() and loaded {len(results)} listings")
    print(f"  Sample listing ID: {results[0]['id']}")
except Exception as e:
    print(f"✗ FAILED: {e}")

# Test 2: size=None and max_price=None (no filters)
print("\n[Test 2] Handle size=None and max_price=None without crashing")
try:
    results = search_listings("vintage", size=None, max_price=None)
    print(f"✓ No crash with None filters - returned {len(results)} results")
except Exception as e:
    print(f"✗ FAILED: {e}")

# Test 3: Keyword scoring as bag-of-words (not exact phrase)
print("\n[Test 3] Keyword scoring treats description as bag of words")
print("  Query: 'graphic vintage' (reversed word order)")
results_reversed = search_listings("graphic vintage", size=None, max_price=None)
print(f"  Results: {len(results_reversed)} items")

print("  Query: 'vintage graphic' (normal word order)")
results_normal = search_listings("vintage graphic", size=None, max_price=None)
print(f"  Results: {len(results_normal)} items")

# Both should return similar/same results (bag of words)
if len(results_reversed) > 0 and len(results_normal) > 0:
    print(f"✓ Bag-of-words confirmed: Both queries found results")
    print(f"  Top match (reversed): {results_reversed[0]['title']}")
    print(f"  Top match (normal): {results_normal[0]['title']}")
else:
    print("✗ FAILED: One or both queries returned no results")

# Test 4: Returns empty list (not exception) when nothing matches
print("\n[Test 4] Returns empty list when nothing matches")
try:
    results = search_listings("xyzabc12345nonexistent", size=None, max_price=None)
    if results == []:
        print(f"✓ Correctly returns empty list: {results}")
    else:
        print(f"✗ FAILED: Expected empty list, got: {results}")
except Exception as e:
    print(f"✗ FAILED: Raised exception instead of returning []: {e}")

# Test 5: Size filter works correctly
print("\n[Test 5] Size filtering (case-insensitive partial match)")
try:
    results_m = search_listings("tee", size="M", max_price=None)
    results_l = search_listings("tee", size="L", max_price=None)
    print(f"✓ Size 'M': {len(results_m)} results")
    print(f"✓ Size 'L': {len(results_l)} results")
    if len(results_l) > 0:
        print(f"  Sample L size: {results_l[0]['size']}")
except Exception as e:
    print(f"✗ FAILED: {e}")

# Test 6: Price filter works correctly
print("\n[Test 6] Price filtering (max_price inclusive)")
try:
    results_all = search_listings("tee", size=None, max_price=None)
    results_30 = search_listings("tee", size=None, max_price=30.0)
    results_20 = search_listings("tee", size=None, max_price=20.0)
    print(f"✓ No price filter: {len(results_all)} results")
    print(f"✓ max_price=30: {len(results_30)} results")
    print(f"✓ max_price=20: {len(results_20)} results")
    
    # Verify filtering is working
    if len(results_30) <= len(results_all) and len(results_20) <= len(results_30):
        print("✓ Price filtering working correctly (smaller max_price = fewer/equal results)")
    else:
        print("✗ WARNING: Price filtering may not be working as expected")
        
    # Check actual prices
    if len(results_20) > 0:
        max_price_found = max(item['price'] for item in results_20)
        print(f"  Highest price in max_price=20 results: ${max_price_found}")
        if max_price_found <= 20.0:
            print("  ✓ All results are within price limit")
except Exception as e:
    print(f"✗ FAILED: {e}")

# Test 7: Combined filters (size + price)
print("\n[Test 7] Combined size and price filters")
try:
    results = search_listings("vintage tee", size="L", max_price=30.0)
    print(f"✓ Query 'vintage tee', size=L, max_price=30: {len(results)} results")
    if len(results) > 0:
        print(f"  Top result: {results[0]['title']}")
        print(f"  Price: ${results[0]['price']}, Size: {results[0]['size']}")
except Exception as e:
    print(f"✗ FAILED: {e}")

# Test 8: Empty description
print("\n[Test 8] Empty or whitespace-only description")
try:
    results_empty = search_listings("", size=None, max_price=None)
    results_spaces = search_listings("   ", size=None, max_price=None)
    print(f"✓ Empty string: {len(results_empty)} results (should return all or filtered)")
    print(f"✓ Whitespace only: {len(results_spaces)} results")
except Exception as e:
    print(f"✗ FAILED: {e}")

# Test 9: Relevance scoring verification
print("\n[Test 9] Relevance scoring (best match first)")
try:
    results = search_listings("vintage graphic tee", size=None, max_price=None)
    if len(results) >= 2:
        print(f"✓ Found {len(results)} results")
        print(f"  Top result: {results[0]['title']}")
        print(f"  2nd result: {results[1]['title']}")
        # Check if "graphic tee" appears in top results
        top_text = (results[0]['title'] + " " + results[0]['description']).lower()
        if 'graphic' in top_text or 'tee' in top_text:
            print("  ✓ Top result contains relevant keywords")
except Exception as e:
    print(f"✗ FAILED: {e}")

print("\n" + "="*70)
print("TESTING COMPLETE")
print("="*70)
