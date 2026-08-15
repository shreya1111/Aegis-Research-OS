"""LangGraph multi-agent layer: graph construction, shared run state, tools, prompts.

Isolated from HTTP and persistence so the graph can be exercised with a stubbed
``LLMProvider`` and a constructed state fixture.
"""
