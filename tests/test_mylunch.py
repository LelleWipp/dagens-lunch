from datetime import date

import pytest

from scraper.sources.base import SourceError
from scraper.sources.mylunch import parse_mylunch

URL = "https://www.mylunch.se/malmo/tugg-burgers/lunch/"


def test_dishes_with_prices_and_descriptions(fixture_html):
    entry = parse_mylunch(fixture_html("mylunch_tugg.html"), date(2026, 11, 5), URL)
    assert entry.status == "today"
    assert [(d.name, d.price) for d in entry.dishes] == [
        ("Dagens lunch på Tugg Burgers från", 109),
        ("Barnmeny", 85),
    ]
    assert entry.dishes[0].desc.startswith("Burgare med fries och kaffe")
    assert entry.dishes[0].kind == "meat"


def test_no_menu_published(fixture_html):
    entry = parse_mylunch(fixture_html("mylunch_vibliotek.html"), date(2026, 11, 5), URL)
    assert entry.status == "none"
    assert entry.note == "No menu published for today"


def test_day_not_on_page(fixture_html):
    assert parse_mylunch(fixture_html("mylunch_tugg.html"), date(2026, 11, 9), URL).status == "none"


def test_changed_layout_raises():
    with pytest.raises(SourceError):
        parse_mylunch("<html><body><div id='other'></div></body></html>", date(2026, 11, 5), URL)
