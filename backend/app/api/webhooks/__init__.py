"""
Webhooks API package exports.
"""

from app.api.webhooks.router import router as webhooks_router

__all__ = ["webhooks_router"]
