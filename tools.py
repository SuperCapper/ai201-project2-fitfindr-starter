"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    # Load all listings
    all_listings = load_listings()

    # Step 1: Filter by max_price and size
    filtered = []
    for listing in all_listings:
        # Price filter
        if max_price is not None and listing["price"] > max_price:
            continue

        # Size filter (case-insensitive partial match)
        if size is not None:
            # Convert both to lowercase for matching
            listing_size_lower = listing["size"].lower()
            size_lower = size.lower()
            if size_lower not in listing_size_lower:
                continue

        filtered.append(listing)

    # If no listings left after filtering, return empty list
    if not filtered:
        return []

    # Step 2: Score each remaining listing by keyword overlap with description
    # Split description into lowercase keywords
    keywords = re.findall(r'\b\w+\b', description.lower())
    # Remove common stop words (optional, but improves relevance)
    stop_words = {"a", "an", "the", "of", "for", "and", "or", "to", "in", "on", "with", "under", "over"}
    keywords = [kw for kw in keywords if kw not in stop_words]

    # If description is empty or no keywords remain, return filtered unsorted
    if not keywords:
        return filtered

    # Score each listing: count how many keywords appear in title or description
    scored = []
    for listing in filtered:
        text = (listing["title"] + " " + listing["description"]).lower()
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scored.append((score, listing))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Return just the listings (without scores)
    return [listing for score, listing in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.
    """
    try:
        client = _get_groq_client()
    except ValueError as e:
        return f"Error: {str(e)}"

    # Check if wardrobe is empty
    wardrobe_items = wardrobe.get("items", [])
    if not wardrobe_items:
        # General styling advice: ask LLM for pairing ideas without wardrobe
        prompt = f"""I just bought a secondhand item: "{new_item['title']}" 
(category: {new_item['category']}, style tags: {', '.join(new_item.get('style_tags', []))}).
Please suggest 1-2 outfit ideas using common clothing categories (e.g., jeans, skirts, jackets, shoes) 
that would pair well with this item. Keep it concise (2-4 sentences)."""
    else:
        # Build a description of the user's wardrobe
        wardrobe_desc = "\n".join(
            f"- {item['name']} ({item['category']}, colors: {', '.join(item.get('colors', []))}, "
            f"tags: {', '.join(item.get('style_tags', []))})"
            for item in wardrobe_items
        )
        prompt = f"""I just bought a secondhand item: "{new_item['title']}" 
(category: {new_item['category']}, style tags: {', '.join(new_item.get('style_tags', []))}).
My existing wardrobe includes:
{wardrobe_desc}
Please suggest 1-2 complete outfits that incorporate the new item with pieces from my wardrobe. 
Be specific (e.g., "Pair it with your baggy jeans and chunky sneakers"). Keep it concise (2-4 sentences)."""

    # Call Groq with low temperature for consistent styling
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful fashion stylist assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200,
        )
        result = response.choices[0].message.content.strip()
        # Ensure non-empty result
        if not result:
            return "No outfit suggestion could be generated. Please try again."
        return result
    except Exception as e:
        return f"Sorry, I couldn't generate an outfit suggestion due to an error: {str(e)}"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)
    """
    # Guard against empty or whitespace-only outfit
    if not outfit or outfit.strip() == "":
        return "Could not create a fit card because the outfit suggestion was missing."

    try:
        client = _get_groq_client()
    except ValueError as e:
        return f"Error: {str(e)}"

    # Build the prompt
    prompt = f"""You are writing an Instagram or TikTok caption for a thrifted outfit. 
The item I bought: "{new_item['title']}" (price: ${new_item['price']}, platform: {new_item.get('platform', 'unknown')}).
Outfit idea: {outfit}
Write a casual, authentic 2-4 sentence caption that:
- Mentions the item name, price, and platform once each.
- Captures the outfit vibe (e.g., "grunge", "cozy", "streetwear").
- Sounds like a real person sharing an OOTD, not a product description.
- Uses emojis sparingly (1-2 max).
Do NOT use hashtags unless they are natural (e.g., #thriftfind is fine)."""

    # Call Groq with higher temperature for variety
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a cool, authentic fashion influencer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,  # higher for variety
            max_tokens=150,
        )
        result = response.choices[0].message.content.strip()
        if not result:
            return "Just snagged this piece — can't wait to style it with my wardrobe!"
        return result
    except Exception as e:
        return f"Could not generate a fit card due to an error: {str(e)}"
