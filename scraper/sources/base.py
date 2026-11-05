"""The Source protocol every source type implements, and the shared error type."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from scraper.models import MenuEntry, Restaurant


class SourceError(Exception):
    """A source could not produce a menu (network, robots.txt, unexpected page). Becomes status 'error'."""


class Source(Protocol):
    def fetch(self, restaurant: Restaurant, day: date) -> MenuEntry:
        """Today's menu for `restaurant`. Raises SourceError (or anything else) when the source breaks."""
        ...
