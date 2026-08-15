"""Routing heuristic between Phase 4 single-shot RAG and the Phase 5 agent
graph (design §6.5 query router: "Runs RAG (Phase 4) or the agent graph
(Phase 5+)"; design §4.2: "a simple factual lookup should not pay the cost
of a full agent graph").

A single question stays on the fast RAG path; a request that visibly asks
for multiple things, or invites comparison/synthesis across sources, needs
the Supervisor to decompose it into subtasks and is routed to the agent
graph instead. This is a deliberately simple, explainable heuristic rather
than a model call of its own — a misclassification only costs latency, never
correctness, since both pipelines produce a cited answer.
"""

from __future__ import annotations

import re

#: Verbs/nouns that signal multi-step research (comparison, gap analysis,
#: synthesis across several sources) rather than a single factual lookup —
#: drawn directly from the Phase 5 acceptance-criteria example question
#: ("compare approach A and B and identify open gaps").
_RESEARCH_KEYWORDS = (
    "compare",
    "comparison",
    "contrast",
    "versus",
    " vs ",
    "gaps",
    "gap analysis",
    "survey",
    "literature review",
    "synthesize",
    "synthesise",
    "synthesis",
    "trends",
    "pros and cons",
    "advantages and disadvantages",
)

#: A request this long is treated as a multi-part research task even without
#: a keyword match — a single factual question rarely needs this many words.
_LONG_REQUEST_WORD_COUNT = 30

_QUESTION_MARK_PATTERN = re.compile(r"\?")


def requires_agent_pipeline(question: str) -> bool:
    """Return ``True`` when ``question`` should run through the Phase 5
    multi-agent graph instead of Phase 4's single-shot RAG."""
    normalised = question.strip().lower()
    if not normalised:
        return False

    if len(_QUESTION_MARK_PATTERN.findall(normalised)) > 1:
        return True

    if any(keyword in normalised for keyword in _RESEARCH_KEYWORDS):
        return True

    return len(normalised.split()) > _LONG_REQUEST_WORD_COUNT
