"""Thin query objects, one per aggregate.

The only place raw SQL is permitted, including future pgvector similarity and
full-text search queries (design §6.6).
"""
