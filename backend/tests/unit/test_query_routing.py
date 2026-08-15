"""Unit tests for the RAG-vs-agent-graph routing heuristic (design §4.2, §6.5)."""

from __future__ import annotations

import pytest

from app.services.query_routing import requires_agent_pipeline


@pytest.mark.unit
def test_a_simple_factual_question_stays_on_the_fast_path() -> None:
    assert requires_agent_pipeline("What is the sample size in this study?") is False


@pytest.mark.unit
def test_a_comparison_request_routes_to_the_agent_graph() -> None:
    """The Phase 5 acceptance-criteria example question."""
    question = "Compare approach A and B and identify open gaps."

    assert requires_agent_pipeline(question) is True


@pytest.mark.unit
def test_a_request_with_multiple_question_marks_routes_to_the_agent_graph() -> None:
    question = "What does the paper conclude? How does that compare to prior work?"

    assert requires_agent_pipeline(question) is True


@pytest.mark.unit
def test_a_long_request_routes_to_the_agent_graph_even_without_a_keyword() -> None:
    question = " ".join(["word"] * 40)

    assert requires_agent_pipeline(question) is True


@pytest.mark.unit
def test_an_empty_question_stays_on_the_fast_path() -> None:
    assert requires_agent_pipeline("   ") is False


@pytest.mark.unit
@pytest.mark.parametrize(
    "keyword",
    ["literature review", "gap analysis", "survey", "synthesize", "trends", "versus"],
)
def test_research_keywords_route_to_the_agent_graph(keyword: str) -> None:
    assert requires_agent_pipeline(f"Please provide a {keyword} of this topic.") is True
