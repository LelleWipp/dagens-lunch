"""Sources that need no network: fixed dishes from config.yaml, and link-only menus."""

from __future__ import annotations

from datetime import date

from scraper.models import MenuEntry, Restaurant


class StaticSource:
    """The same dishes every day, listed in config.yaml (status 'standing')."""

    def fetch(self, restaurant: Restaurant, day: date) -> MenuEntry:
        assert restaurant.source is not None
        return MenuEntry(status="standing", dishes=restaurant.source.dishes, source=restaurant.source.url)


class LinkSource:
    """The menu is only available behind a link we must not scrape, e.g. Instagram (status 'link')."""

    def fetch(self, restaurant: Restaurant, day: date) -> MenuEntry:
        assert restaurant.source is not None
        return MenuEntry(status="link", source=restaurant.source.url)
