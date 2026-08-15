"""HTTP layer: routers, shared dependencies, request/response wiring.

The only layer aware of HTTP. Routers stay thin — validate, authorise, delegate
to a service, shape the response.
"""
