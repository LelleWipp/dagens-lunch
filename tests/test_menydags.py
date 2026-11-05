from datetime import date

import pytest

from scraper.sources.base import SourceError
from scraper.sources.menydags import parse_menydags

URL = "https://www.menydags.se/restaurang/kol-cocktails-malmo/lunch"


def test_picks_todays_section(fixture_html):
    entry = parse_menydags(fixture_html("menydags_kol.html"), date(2026, 11, 5), URL)
    assert entry.status == "today"
    assert entry.source == URL
    assert [d.name for d in entry.dishes][:3] == ["Mixed grill", "Halstrad lax", "Friterad halloumi"]
    assert len(entry.dishes) == 7


def test_other_day_gives_other_dishes(fixture_html):
    wednesday = parse_menydags(fixture_html("menydags_kol.html"), date(2026, 11, 4), URL)
    friday = parse_menydags(fixture_html("menydags_kol.html"), date(2026, 11, 6), URL)
    assert wednesday.dishes[0].name == "Pannbiff"
    assert friday.dishes[0].name == "Grillad högrevsburgare"


def test_prices_kinds_and_descriptions(fixture_html):
    dishes = {
        d.name: d for d in parse_menydags(fixture_html("menydags_kol.html"), date(2026, 11, 5), URL).dishes
    }
    assert dishes["Mixed grill"].price is None  # no offer in the source
    assert dishes["Mixed grill"].kind == "meat"
    assert dishes["Halstrad lax"].price == 185
    assert dishes["Halstrad lax"].kind == "fish"
    assert dishes["Friterad halloumi"].kind == "veg"  # suitableForDiet: VegetarianDiet
    assert dishes["Tuna"].kind == "fish"
    assert dishes["Sirloin"].desc.startswith("Hängmörad ryggbiff")


def test_day_without_section_is_none(fixture_html):
    entry = parse_menydags(fixture_html("menydags_kol.html"), date(2026, 11, 9), URL)
    assert entry.status == "none"
    assert entry.dishes == ()


def test_page_without_menu_raises():
    with pytest.raises(SourceError):
        parse_menydags("<html><head></head><body>Ny layout</body></html>", date(2026, 11, 5), URL)
