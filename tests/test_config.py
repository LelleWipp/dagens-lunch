from pathlib import Path

import pytest

from scraper.config import ConfigError, load_config, parse_config

ROOT = Path(__file__).resolve().parent.parent


def minimal(**restaurant):
    return {
        "office": {"name": "Kontoret", "address": "Gatan 1", "lat": 55.6, "lon": 13.0},
        "restaurants": [{"id": "a", "name": "A", "lat": 55.6, "lon": 13.0, **restaurant}],
    }


def test_repo_config_is_valid():
    config = load_config(ROOT / "config.yaml")
    assert len(config.restaurants) >= 10
    scraped = [r for r in config.restaurants if r.source and r.source.type in ("menydags", "mylunch")]
    assert len(scraped) >= 6  # Definition of done: at least 6 restaurants fetched automatically


def test_defaults():
    config = parse_config(minimal())
    assert config.office.timezone == "Europe/Stockholm"
    assert config.office.radius_m == 500
    assert config.walk_speed_m_per_min == 80
    assert config.restaurants[0].source is None


@pytest.mark.parametrize(
    ("restaurant", "message"),
    [
        ({"source": {"type": "facebook", "url": "https://x.example"}}, "source type"),
        ({"source": {"type": "menydags", "url": "ftp://x.example"}}, "https://"),
        ({"source": {"type": "static", "url": "https://x.example"}}, "at least one dish"),
        (
            {
                "source": {
                    "type": "static",
                    "url": "https://x.example",
                    "dishes": [{"name": "X", "kind": "pizza"}],
                }
            },
            "kind",
        ),
        ({"lat": "north"}, "'lat' must be a number"),
    ],
)
def test_invalid_restaurant(restaurant, message):
    with pytest.raises(ConfigError, match=message):
        parse_config(minimal(**restaurant))


def test_duplicate_ids():
    raw = minimal()
    raw["restaurants"].append(dict(raw["restaurants"][0]))
    with pytest.raises(ConfigError, match="duplicate"):
        parse_config(raw)


def test_unknown_timezone():
    raw = minimal()
    raw["office"]["timezone"] = "Mars/Olympus"
    with pytest.raises(ConfigError, match="timezone"):
        parse_config(raw)
