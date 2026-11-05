"""mylunch.se: one <div id="wdDDMM"> per day; rows of p.mim-txt (dish) + p.mim-prc (price),
optionally followed by a row with p.mim-txt0 (description of the dish above)."""

from __future__ import annotations

from datetime import date

from selectolax.parser import HTMLParser

from scraper.models import Dish, MenuEntry, Restaurant
from scraper.normalize import classify_dish, clean_text, parse_price
from scraper.sources.base import SourceError
from scraper.sources.http import PoliteClient

_NO_MENU_TEXT = "det finns ingen meny"


class MylunchSource:
    def __init__(self, client: PoliteClient) -> None:
        self._client = client

    def fetch(self, restaurant: Restaurant, day: date) -> MenuEntry:
        assert restaurant.source is not None
        url = restaurant.source.url
        return parse_mylunch(self._client.get_text(url), day, url)


def parse_mylunch(html: str, day: date, url: str) -> MenuEntry:
    tree = HTMLParser(html)
    if tree.css_first("#menus") is None:
        raise SourceError("no #menus block on the page; the layout may have changed")
    day_block = tree.css_first(f"#wd{day:%d%m}")
    if day_block is None:
        return MenuEntry(status="none", note="No menu published for today", source=url)

    rows: list[tuple[str, str, int | None]] = []  # (name, desc, price)
    for row in day_block.css(".mim-row"):
        name_node = row.css_first("p.mim-txt")
        desc_node = row.css_first("p.mim-txt0")
        price_node = row.css_first("p.mim-prc")
        price = parse_price(price_node.text(strip=True)) if price_node else None
        if name_node is not None:
            name = clean_text(name_node.text())
            if name:
                rows.append((name, "", price))
        elif desc_node is not None and rows:
            desc = clean_text(desc_node.text())
            if desc:
                name, old_desc, old_price = rows[-1]
                rows[-1] = (name, (old_desc + " " + desc).strip(), old_price)

    if not rows:
        text = clean_text(day_block.text()).lower()
        note = "No menu published for today" if _NO_MENU_TEXT in text else ""
        return MenuEntry(status="none", note=note, source=url)
    dishes = tuple(Dish(name=n, desc=d, price=p, kind=classify_dish(n, d)) for n, d, p in rows)
    return MenuEntry(status="today", dishes=dishes, source=url)
