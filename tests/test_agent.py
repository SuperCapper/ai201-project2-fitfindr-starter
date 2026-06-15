# tests/test_agent.py
"""
Integration tests for the run_agent() planning loop.

These cover the planning loop, state management, and error handling promised
in planning.md (Milestone 4), plus the query-parsing behavior. The LLM-backed
tools are patched at the agent module level so the loop is exercised
deterministically without live Groq calls.
"""
from unittest.mock import patch, MagicMock

import agent
from tools import ToolError


# ── happy path ─────────────────────────────────────────────────────────────────

@patch("agent.create_fit_card", return_value="A shareable fit card caption.")
@patch("agent.suggest_outfit", return_value="Pair it with baggy jeans and sneakers.")
def test_run_agent_happy_path(mock_suggest, mock_create):
    from utils.data_loader import get_example_wardrobe

    session = agent.run_agent("vintage graphic tee under $30", get_example_wardrobe())

    assert session["error"] is None
    assert session["selected_item"] is not None
    assert session["search_results"]                      # non-empty
    assert session["outfit_suggestion"] == "Pair it with baggy jeans and sneakers."
    assert session["fit_card"] == "A shareable fit card caption."
    assert session["parsed"]["max_price"] == 30.0
    mock_suggest.assert_called_once()
    mock_create.assert_called_once()


# ── early-return branches ───────────────────────────────────────────────────────

@patch("agent.create_fit_card")
@patch("agent.suggest_outfit")
def test_run_agent_no_results(mock_suggest, mock_create):
    from utils.data_loader import get_example_wardrobe

    session = agent.run_agent("designer ballgown size XXS under $5", get_example_wardrobe())

    assert "No listings found" in session["error"]
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
    # Downstream tools must not be called once search returns nothing.
    mock_suggest.assert_not_called()
    mock_create.assert_not_called()


@patch("agent.create_fit_card")
@patch("agent.suggest_outfit")
def test_run_agent_no_results_suggests_size_adjustment(mock_suggest, mock_create):
    # When a size filter is set, the no-results message names that size.
    session = agent.run_agent("designer ballgown size XXS under $5", {"items": []})
    assert session["error"].startswith("No listings found")
    assert "XXS" in session["error"]
    mock_suggest.assert_not_called()
    mock_create.assert_not_called()


@patch("agent.create_fit_card")
@patch("agent.suggest_outfit")
def test_run_agent_no_results_suggests_price_adjustment(mock_suggest, mock_create):
    # Price filter, no size -> suggests raising the price limit.
    session = agent.run_agent("designer ballgown under $1", {"items": []})
    assert session["error"].startswith("No listings found")
    assert "price" in session["error"].lower()
    mock_suggest.assert_not_called()


@patch("agent.create_fit_card")
@patch("agent.suggest_outfit")
def test_run_agent_no_results_suggests_keywords(mock_suggest, mock_create):
    # No size, no price -> falls back to a keyword hint.
    session = agent.run_agent("zzz nonexistent item", {"items": []})
    assert session["error"].startswith("No listings found")
    assert "keyword" in session["error"].lower()
    mock_suggest.assert_not_called()


@patch("agent.create_fit_card")
@patch("agent.suggest_outfit", side_effect=ToolError("LLM down"))
def test_run_agent_suggest_outfit_failure(mock_suggest, mock_create):
    from utils.data_loader import get_example_wardrobe

    session = agent.run_agent("vintage graphic tee under $30", get_example_wardrobe())

    assert session["error"] == "Could not generate an outfit suggestion. Please try again."
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
    mock_create.assert_not_called()


@patch("agent.create_fit_card", side_effect=ToolError("LLM down"))
@patch("agent.suggest_outfit", return_value="Pair it with baggy jeans and sneakers.")
def test_run_agent_create_fit_card_failure(mock_suggest, mock_create):
    from utils.data_loader import get_example_wardrobe

    session = agent.run_agent("vintage graphic tee under $30", get_example_wardrobe())

    assert session["error"] == "Could not create a fit card."
    assert session["outfit_suggestion"] == "Pair it with baggy jeans and sneakers."
    assert session["fit_card"] is None


@patch("agent.create_fit_card", return_value="caption")
@patch("agent.suggest_outfit", return_value="advice")
def test_run_agent_empty_wardrobe_is_not_an_error(mock_suggest, mock_create):
    from utils.data_loader import get_empty_wardrobe

    session = agent.run_agent("vintage graphic tee under $30", get_empty_wardrobe())

    assert session["error"] is None
    assert session["fit_card"] == "caption"


def test_run_agent_empty_description():
    # A query with only a price (no describable text) cannot be searched.
    session = agent.run_agent("$30", {"items": []})
    assert "Please describe what you're looking for" in session["error"]
    assert session["search_results"] == []


# ── query parsing (bug-3 fix: size regex no longer over-captures) ───────────────

@patch("agent.create_fit_card", return_value="caption")
@patch("agent.suggest_outfit", return_value="advice")
def test_parse_size_does_not_swallow_trailing_words(mock_suggest, mock_create):
    from utils.data_loader import get_example_wardrobe

    session = agent.run_agent("vintage tee size M cotton crewneck", get_example_wardrobe())
    assert session["parsed"]["size"] == "M"
    # Trailing prose stays in the description, not the size.
    assert "cotton" in session["parsed"]["description"].lower()


@patch("agent.create_fit_card", return_value="caption")
@patch("agent.suggest_outfit", return_value="advice")
def test_parse_waist_length_size(mock_suggest, mock_create):
    from utils.data_loader import get_example_wardrobe

    session = agent.run_agent("baggy jeans size W30 L30", get_example_wardrobe())
    assert session["parsed"]["size"] == "W30 L30"


@patch("agent.create_fit_card", return_value="caption")
@patch("agent.suggest_outfit", return_value="advice")
def test_parse_price(mock_suggest, mock_create):
    from utils.data_loader import get_example_wardrobe

    session = agent.run_agent("flowy midi skirt under $40", get_example_wardrobe())
    assert session["parsed"]["max_price"] == 40.0
