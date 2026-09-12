"""Backward-compatible import: FastAPI app lives in server.app."""

from server.app import create_app

__all__ = ["create_app"]
