"""Supadata web scrape rung for resilient-search."""

from __future__ import annotations

from .provider import SupadataExtractProvider


def register(ctx) -> None:
    ctx.register_web_search_provider(SupadataExtractProvider())
