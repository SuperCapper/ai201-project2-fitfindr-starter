# tests/test_app.py
"""
Tests for the Gradio handler handle_query() in app.py.

run_agent is patched so we test only the handler's responsibilities:
the empty-query guard, wardrobe selection, error -> first-panel mapping,
and formatting the session into the three output panels.
"""
from unittest.mock import patch

import app


def _ok_session():
    return {
        "error": None,
        "selected_item": {
            "title": "Graphic Tee — 2003 Tour Bootleg Style",
            "price": 24.0,
            "platform": "depop",
            "condition": "good",
            "size": "L",
            "category": "tops",
            "style_tags": ["graphic tee", "vintage"],
            "colors": ["black"],
            "brand": "None",
            "description": "A faded bootleg tour tee.",
        },
        "outfit_suggestion": "Pair it with baggy jeans and sneakers.",
        "fit_card": "Just snagged this tee for $24 on Depop! #thriftfind",
    }


def test_handle_query_empty_guard():
    listing, outfit, card = app.handle_query("", "Example wardrobe")
    assert listing.startswith("⚠")        # warning sign
    assert outfit == ""
    assert card == ""


@patch("app.run_agent")
def test_handle_query_error_path(mock_run_agent):
    mock_run_agent.return_value = {
        "error": "No listings found. Try a different size (e.g., remove the 'XXS' filter).",
        "selected_item": None,
        "outfit_suggestion": None,
        "fit_card": None,
    }
    listing, outfit, card = app.handle_query("designer ballgown under $5", "Example wardrobe")
    assert "No listings found" in listing
    assert outfit == ""
    assert card == ""


@patch("app.run_agent")
def test_handle_query_success_maps_panels(mock_run_agent):
    mock_run_agent.return_value = _ok_session()
    listing, outfit, card = app.handle_query("vintage graphic tee under $30", "Example wardrobe")

    # Panel 1: formatted listing with key fields.
    assert "Graphic Tee — 2003 Tour Bootleg Style" in listing
    assert "$24.00" in listing
    assert "depop" in listing
    # Panels 2 and 3 pass the session values straight through.
    assert outfit == "Pair it with baggy jeans and sneakers."
    assert card == "Just snagged this tee for $24 on Depop! #thriftfind"


@patch("app.get_empty_wardrobe")
@patch("app.get_example_wardrobe")
@patch("app.run_agent", return_value=_ok_session())
def test_handle_query_selects_wardrobe(mock_run_agent, mock_example, mock_empty):
    app.handle_query("vintage tee", "Example wardrobe")
    mock_example.assert_called_once()
    mock_empty.assert_not_called()

    mock_example.reset_mock()
    app.handle_query("vintage tee", "Empty wardrobe (new user)")
    mock_empty.assert_called_once()
    mock_example.assert_not_called()
