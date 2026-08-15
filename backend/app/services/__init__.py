"""Business logic.

HTTP-free by design, so every service is unit-testable without a request. Services
accept and return Pydantic models and may call other services; nothing here imports
FastAPI request objects.
"""
