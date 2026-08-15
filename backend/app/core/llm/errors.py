"""Typed provider-call outcomes, internal to the LLM layer."""

from __future__ import annotations


class TransientProviderError(Exception):
    """A provider call failed in a way worth retrying (timeout, 5xx, 429)."""


class FatalProviderError(Exception):
    """A provider call failed in a way retrying cannot fix (4xx other than 429)."""
