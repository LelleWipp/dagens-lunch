import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scraper.build import build_daily_menu, distance_m, fetch_entry, to_json_text
from scraper.config import load_config, parse_config
from scraper.models import Dish, MenuEntry, Restaurant, SourceConfig
from scraper.sources.base import SourceError

ROOT = Path(__file__).resolve().parent.parent
DAY = date(2026, 11, 5)
NOW = datetime(2026, 11, 5, 9, 47, tzinfo=ZoneInfo("Europe/Stockholm"))


class Broken:
    def fetch(self, restaurant, day):
        raise SourceError("site is down")


class Fixed:
    def fetch(self, restaurant, day):
        return MenuEntry(status="today", dishes=(Dish(name="Soppa", kind="veg", price=95),))


def restaurant(rid: str, source_type: str | None) -> Restaurant:
    source = SourceConfig(type=source_type, url=f"https://{rid}.example/") if source_type else None
    return Restaurant(id=rid, name=rid.upper(), lat=55.6, lon=13.0, source=source)


def test_distances_match_prototype_data():
    # menus.json from the prototype carries distances computed from the same coordinates.
    config = load_config(ROOT / "config.yaml")
    prototype = {
        r["id"]: r["distance_m"]
        for r in json.loads((ROOT / "docs/data/archive/2026-10-22.json").read_text())["restaurants"]
    }
    for r in config.restaurants:
        assert abs(distance_m(config.office.lat, config.office.lon, r.lat, r.lon) - prototype[r.id]) <= 1, (
            r.id
        )


def test_a_broken_source_does_not_stop_the_others():
    sources = {"broken": Broken(), "fixed": Fixed()}
    broken = fetch_entry(restaurant("a", "broken"), DAY, sources)
    fixed = fetch_entry(restaurant("b", "fixed"), DAY, sources)
    assert broken.status == "error"
    assert broken.source == "https://a.example/"
    assert fixed.status == "today"


def test_restaurant_without_source_is_none():
    assert fetch_entry(restaurant("c", None), DAY, {}).status == "none"


def test_output_follows_the_json_contract():
    config = parse_config(
        {
            "office": {
                "name": "Kontoret",
                "address": "Gatan 1",
                "lat": 55.6056,
                "lon": 13.0003,
                "radius_m": 400,
            },
            "walk_speed_m_per_min": 75,
            "restaurants": [
                {"id": "a", "name": "A", "lat": 55.6055, "lon": 12.9992, "hours": "11–14", "favourite": True},
                {"id": "b", "name": "B", "lat": 55.6061, "lon": 12.9977},
            ],
        }
    )
    entries = {
        "a": MenuEntry(
            status="today",
            dishes=(Dish(name="Lax", kind="fish", price=130, desc="Med dill"),),
            source="https://a.example/",
        )
    }
    data = json.loads(to_json_text(build_daily_menu(config, entries, DAY, NOW)))

    # The fields docs/app.js reads; see "JSON-kontraktet" in CLAUDE.md.
    assert set(data) == {"date", "updated_at", "office", "walk_speed_m_per_min", "restaurants", "items"}
    assert data["date"] == "2026-11-05"
    assert data["updated_at"] == "2026-11-05T09:47:00+01:00"
    assert data["office"] == {"name": "Kontoret", "address": "Gatan 1", "radius_m": 400}
    assert data["walk_speed_m_per_min"] == 75
    first = data["restaurants"][0]
    assert first == {"id": "a", "name": "A", "hours": "11–14", "favourite": True, "distance_m": 70}
    assert "lat" not in first and "source" not in first
    assert data["items"]["a"] == {
        "status": "today",
        "dishes": [{"name": "Lax", "desc": "Med dill", "kind": "fish", "price": 130}],
        "source": "https://a.example/",
    }
    # every restaurant gets an entry, so the frontend never has to guess
    assert data["items"]["b"] == {"status": "none", "dishes": []}
    allowed_status = {"today", "standing", "link", "none", "error"}
    assert all(item["status"] in allowed_status for item in data["items"].values())
