from datetime import date

import pytest

from scraper.normalize import classify_dish, clean_text, parse_price, parse_swedish_day


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("185", 185),
        ("109Kr", 109),
        ("129 kr", 129),
        ("fr. 99 kr", 99),
        (145.0, 145),
        (None, None),
        ("", None),
        ("Kr", None),
    ],
)
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


@pytest.mark.parametrize(
    ("name", "desc", "expected"),
    [
        ("Pannbiff", "Potatismos, gräddsås", "meat"),
        ("Halstrad lax", "Örtslungad potatis", "fish"),
        ("Bönbiff", "Med rotfrukter", "veg"),
        ("Lunchbuffé", "Pizza, pasta och sallad", "buffet"),
        ("Bibimbap", "Välj mellan kyckling eller friterad tofu", "other"),
        ("Dagens husman", "Stekt lax med dillsås", "fish"),
        ("Pasta", "", "other"),
        ("Sotad gravlax", "Dillstuvad potatis", "fish"),
        ("Stekt falukorv", "Stuvade makaroner", "meat"),
        ("Grillad högrevsburgare", "Pommes frites", "meat"),
        ("Träkolsgrillad kyckling", "", "meat"),
        ("Salladsbuffé", "", "buffet"),
        ("Bento Yakiniku", "Kålsallad, 4 nigiri, veganska dumplings", "meat"),
        ("Dagens bowl", "Tofu eller kyckling", "other"),
        ("Veckans sallad", "Vegansk dressing, rökt lax", "other"),
    ],
)
def test_classify_dish(name, desc, expected):
    assert classify_dish(name, desc) == expected


def test_vegetarian_hint_wins_unless_buffet():
    assert classify_dish("Friterad halloumi", "", vegetarian=True) == "veg"
    assert classify_dish("Vegetarisk buffé", "", vegetarian=True) == "buffet"


def test_clean_text():
    assert clean_text("  Tofu-\u00a0 &  avokado\nrulle ") == "Tofu- & avokado rulle"
    assert clean_text(None) == ""


def test_parse_swedish_day():
    assert parse_swedish_day("Torsdag 5 november", 2026) == date(2026, 11, 5)
    assert parse_swedish_day("Måndag 29 december", 2026) == date(2026, 12, 29)
    assert parse_swedish_day("Alla dagar", 2026) is None
    assert parse_swedish_day("Fredag 31 februari", 2026) is None
