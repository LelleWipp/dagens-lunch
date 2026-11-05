"""Builds docs/data/menus.json from config.yaml.

Everything above main() is pure (data in, data out). main() is the only part that touches the
network (through scraper.sources) and the file system. Run with:  python -m scraper.build
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scraper.config import load_config
from scraper.models import Config, DailyMenu, MenuEntry, Restaurant
from scraper.sources import PoliteClient, Source, make_sources

log = logging.getLogger("scraper")

ROOT = Path(__file__).resolve().parent.parent
EARTH_RADIUS_M = 6_371_000
NETWORK_TYPES = ("menydags", "mylunch")


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Straight-line (haversine) distance in whole metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * EARTH_RADIUS_M * math.asin(math.sqrt(h)))


def fetch_entry(restaurant: Restaurant, day: date, sources: Mapping[str, Source]) -> MenuEntry:
    """Runs one restaurant's source in isolation: any failure becomes status 'error'.

    CLAUDE.md: a source that breaks must never stop the others.
    """
    if restaurant.source is None:
        return MenuEntry(status="none")
    try:
        return sources[restaurant.source.type].fetch(restaurant, day)
    except Exception as err:  # isolation is the point; the error is logged below
        log.warning("%s: %s failed: %s", restaurant.id, restaurant.source.type, err)
        return MenuEntry(status="error", source=restaurant.source.url)


def build_daily_menu(
    config: Config, entries: Mapping[str, MenuEntry], day: date, updated_at: datetime
) -> DailyMenu:
    office = config.office
    return DailyMenu(
        day=day,
        updated_at=updated_at,
        office=office,
        walk_speed_m_per_min=config.walk_speed_m_per_min,
        restaurants=tuple((r, distance_m(office.lat, office.lon, r.lat, r.lon)) for r in config.restaurants),
        items={r.id: entries.get(r.id, MenuEntry(status="none")) for r in config.restaurants},
    )


def to_json_text(menu: DailyMenu) -> str:
    return json.dumps(menu.to_json(), ensure_ascii=False, indent=2) + "\n"


def summarize(entries: Mapping[str, MenuEntry]) -> str:
    counts: dict[str, int] = {}
    for entry in entries.values():
        counts[entry.status] = counts.get(entry.status, 0) + 1
    return ", ".join(f"{status}: {n}" for status, n in sorted(counts.items()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch today's lunch menus into menus.json.")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "data")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    config = load_config(args.config)
    now = datetime.now(ZoneInfo(config.office.timezone))
    day = now.date()

    client = PoliteClient()
    try:
        sources = make_sources(client)
        entries = {r.id: fetch_entry(r, day, sources) for r in config.restaurants}
    finally:
        client.close()

    text = to_json_text(build_daily_menu(config, entries, day, now))
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "archive").mkdir(exist_ok=True)
    (args.out / "menus.json").write_text(text, encoding="utf-8")
    (args.out / "archive" / f"{day.isoformat()}.json").write_text(text, encoding="utf-8")
    log.info("%s: %s", day.isoformat(), summarize(entries))
    # A run where every scraped source failed is most likely a network or layout problem.
    scraped = [entries[r.id] for r in config.restaurants if r.source and r.source.type in NETWORK_TYPES]
    if scraped and all(e.status == "error" for e in scraped):
        log.error("every scraped source failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
