"""menydags.se: reads the schema.org Menu in the page's JSON-LD (one MenuSection per weekday).

Using the structured data instead of CSS classes keeps the parser working when the layout changes.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from selectolax.lexbor import LexborHTMLParser

from scraper.models import Dish, MenuEntry, Restaurant
from scraper.normalize import classify_dish, clean_text, parse_price, parse_swedish_day
from scraper.sources.base import SourceError
from scraper.sources.http import PoliteClient

_VEGETARIAN_DIETS = ("VegetarianDiet", "VeganDiet")
_SCRIPT_BODY = re.compile(r"^<script[^>]*>(.*)</script>\s*$", re.DOTALL | re.IGNORECASE)


class MenydagsSource:
    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch(self, restaurant: Restaurant, day: date) -> MenuEntry:
        assert restaurant.source is not None
        url = restaurant.source.url
        return parse_menydags(self._client.get_text(url), day, url)


def parse_menydags(html: str, day: date, url: str) -> MenuEntry:
    menu = _find_menu(html)
    if menu is None:
        raise SourceError("no schema.org Menu found in the page's JSON-LD")
    for section in _as_list(menu.get("hasMenuSection")):
        if parse_swedish_day(str(section.get("name", "")), day.year) == day:
            dishes = tuple(_dish(item) for item in _as_list(section.get("hasMenuItem")))
            dishes = tuple(d for d in dishes if d.name)
            if dishes:
                return MenuEntry(status="today", dishes=dishes, source=url)
    return MenuEntry(status="none", note="No menu published for today", source=url)


def _find_menu(html: str) -> dict[str, Any] | None:
    for node in LexborHTMLParser(html).css('script[type="application/ld+json"]'):
        try:
            data = json.loads(_script_body(node.text(deep=True), node.html or ""))
        except json.JSONDecodeError:
            continue
        candidates = data.get("@graph", [data]) if isinstance(data, dict) else data
        for candidate in _as_list(candidates):
            if isinstance(candidate, dict) and candidate.get("@type") == "Menu":
                return candidate
    return None


def _script_body(text: str, outer_html: str) -> str:
    """Script contents; falls back to the raw markup in case the parser keeps script text out of text()."""
    if text.strip():
        return text
    match = _SCRIPT_BODY.match(outer_html.strip())
    return match.group(1) if match else ""


def _dish(item: dict[str, Any]) -> Dish:
    name = clean_text(item.get("name"))
    desc = clean_text(item.get("description"))
    offers = item.get("offers")
    price = parse_price(offers.get("price")) if isinstance(offers, dict) else None
    diets = " ".join(str(d) for d in _as_list(item.get("suitableForDiet")))
    vegetarian = any(diet in diets for diet in _VEGETARIAN_DIETS)
    return Dish(name=name, desc=desc, price=price, kind=classify_dish(name, desc, vegetarian))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]
