# tests/test_tools.py
import pytest
from unittest.mock import patch, MagicMock

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import load_listings, get_example_wardrobe, get_empty_wardrobe


# ── search_listings tests ─────────────────────────────────────────────────────

def test_search_returns_results():
    """Test that search_listings returns a non-empty list for a valid query."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    # Each result should be a dict with expected keys
    for item in results:
        assert isinstance(item, dict)
        assert "id" in item
        assert "title" in item


def test_search_empty_results():
    """Test that search_listings returns an empty list when no matches exist (not an exception)."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []  # empty list, no exception


def test_search_price_filter():
    """Test that search_listings respects max_price filter."""
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


def test_search_size_filter():
    """Test that search_listings respects size filter (case-insensitive partial match)."""
    # Search for size "M" — should match "M", "S/M", "M/L", etc.
    results = search_listings("shirt", size="M", max_price=None)
    for item in results:
        assert "m" in item["size"].lower()


def test_search_no_keywords():
    """Test that search_listings handles empty description or stop-word-only description."""
    results = search_listings("a an the of", size=None, max_price=None)
    # Should return all listings (since no meaningful keywords) or at least not crash
    assert isinstance(results, list)


# ── suggest_outfit tests ──────────────────────────────────────────────────────

@patch("tools._get_groq_client")
def test_suggest_outfit_empty_wardrobe(mock_get_groq_client):
    """Test that suggest_outfit handles empty wardrobe by returning general styling advice."""
    # Mock the Groq client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Style it with jeans and a jacket."))]
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_groq_client.return_value = mock_client

    # Get a sample item
    listings = load_listings()
    item = listings[0]  # lst_001

    # Empty wardrobe
    empty_wardrobe = get_empty_wardrobe()

    result = suggest_outfit(item, empty_wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0
    # Should not be an error message
    assert "Error" not in result
    # Verify the mock was called with the correct prompt
    prompt = mock_client.chat.completions.create.call_args[1]["messages"][1]["content"]
    assert "common clothing categories" in prompt.lower()


@patch("tools._get_groq_client")
def test_suggest_outfit_with_wardrobe(mock_get_groq_client):
    """Test that suggest_outfit works with a non-empty wardrobe."""
    # Mock the Groq client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Pair with your baggy jeans and chunky sneakers."))]
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_groq_client.return_value = mock_client

    # Get a sample item
    listings = load_listings()
    item = listings[0]  # lst_001

    # Example wardrobe
    wardrobe = get_example_wardrobe()

    result = suggest_outfit(item, wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0
    # Verify the mock was called with the correct prompt
    prompt = mock_client.chat.completions.create.call_args[1]["messages"][1]["content"]
    assert "My existing wardrobe includes:" in prompt


@patch("tools._get_groq_client")
def test_suggest_outfit_api_failure(mock_get_groq_client):
    """Test that suggest_outfit handles API failures gracefully."""
    # Mock the Groq client to raise an exception
    mock_get_groq_client.side_effect = Exception("API error")

    # Get a sample item
    listings = load_listings()
    item = listings[0]  # lst_001
    wardrobe = get_example_wardrobe()

    result = suggest_outfit(item, wardrobe)
    assert isinstance(result, str)
    assert "Error:" in result
    assert "API error" in result


def test_suggest_outfit_missing_groq_key():
    """Test that suggest_outfit handles missing GROQ_API_KEY."""
    # Save the original environment and clear GROQ_API_KEY
    import os
    original_key = os.environ.get("GROQ_API_KEY")
    os.environ["GROQ_API_KEY"] = ""  # Empty
    
    try:
        # This will fail because _get_groq_client will raise ValueError
        listings = load_listings()
        item = listings[0]
        wardrobe = get_example_wardrobe()
        
        # The function should catch the ValueError and return an error string
        result = suggest_outfit(item, wardrobe)
        assert isinstance(result, str)
        assert "Error:" in result or "GROQ_API_KEY" in result
    finally:
        # Restore the original key
        if original_key:
            os.environ["GROQ_API_KEY"] = original_key
        else:
            del os.environ["GROQ_API_KEY"]


# ── create_fit_card tests ─────────────────────────────────────────────────────

def test_create_fit_card_empty_outfit():
    """Test that create_fit_card returns an error message when outfit is empty."""
    listings = load_listings()
    item = listings[0]
    
    result = create_fit_card("", item)
    assert "Could not create a fit card" in result
    
    result = create_fit_card("   ", item)
    assert "Could not create a fit card" in result


@patch("tools._get_groq_client")
def test_create_fit_card_valid(mock_get_groq_client):
    """Test that create_fit_card works with valid inputs."""
    # Mock the Groq client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Just snagged this vintage tee for $24 on Depop! #thriftfind"))]
    mock_client.chat.completions.create.return_value = mock_response
    mock_get_groq_client.return_value = mock_client

    listings = load_listings()
    item = listings[0]
    outfit = "Pair with your baggy jeans and chunky sneakers."

    result = create_fit_card(outfit, item)
    assert isinstance(result, str)
    assert len(result) > 0
    # Verify the mock was called
    assert mock_client.chat.completions.create.called


@patch("tools._get_groq_client")
def test_create_fit_card_api_failure(mock_get_groq_client):
    """Test that create_fit_card handles API failures gracefully."""
    # Mock the Groq client to raise an exception
    mock_get_groq_client.side_effect = Exception("API error")

    listings = load_listings()
    item = listings[0]
    outfit = "Pair with your baggy jeans and chunky sneakers."

    result = create_fit_card(outfit, item)
    assert isinstance(result, str)
    assert "Error:" in result
    assert "API error" in result


def test_create_fit_card_missing_groq_key():
    """Test that create_fit_card handles missing GROQ_API_KEY."""
    import os
    original_key = os.environ.get("GROQ_API_KEY")
    os.environ["GROQ_API_KEY"] = ""  # Empty
    
    try:
        listings = load_listings()
        item = listings[0]
        outfit = "Pair with your baggy jeans and chunky sneakers."
        
        result = create_fit_card(outfit, item)
        assert isinstance(result, str)
        assert "Error:" in result or "GROQ_API_KEY" in result
    finally:
        if original_key:
            os.environ["GROQ_API_KEY"] = original_key
        else:
            del os.environ["GROQ_API_KEY"]
