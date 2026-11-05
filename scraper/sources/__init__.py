"""Registry of source types. A new type is one module here plus one entry in make_sources()."""

from __future__ import annotations

from scraper.sources.base import Source, SourceError
from scraper.sources.http import PoliteClient
from scraper.sources.menydags import MenydagsSource
from scraper.sources.mylunch import MylunchSource
from scraper.sources.static import LinkSource, StaticSource

__all__ = ["PoliteClient", "Source", "SourceError", "make_sources"]


def make_sources(client: PoliteClient) -> dict[str, Source]:
    """Maps the `type` in config.yaml to the Source that handles it."""
    return {
        "menydags": MenydagsSource(client),
        "mylunch": MylunchSource(client),
        "static": StaticSource(),
        "link": LinkSource(),
    }
