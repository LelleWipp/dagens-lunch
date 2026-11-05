"""Reads and validates config.yaml. Raises ConfigError with a message that names the bad field."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from scraper.models import KINDS, Config, Dish, Office, Restaurant, SourceConfig
from scraper.normalize import clean_text

SOURCE_TYPES = ("menydags", "mylunch", "static", "link")


class ConfigError(ValueError):
    pass


def load_config(path: Path) -> Config:
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return parse_config(raw)


def parse_config(raw: Any) -> Config:
    if not isinstance(raw, dict):
        raise ConfigError("config.yaml must be a mapping with office and restaurants")
    office = _parse_office(_require(raw, "office", dict, "config"))
    restaurants = tuple(
        _parse_restaurant(r, i) for i, r in enumerate(_require(raw, "restaurants", list, "config"))
    )
    ids = [r.id for r in restaurants]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ConfigError(f"duplicate restaurant id(s): {', '.join(duplicates)}")
    walk_speed = raw.get("walk_speed_m_per_min", 80)
    if not isinstance(walk_speed, int) or walk_speed <= 0:
        raise ConfigError("walk_speed_m_per_min must be a positive integer")
    return Config(office=office, walk_speed_m_per_min=walk_speed, restaurants=restaurants)


def _require(data: dict[str, Any], key: str, kind: type, where: str) -> Any:
    value = data.get(key)
    if not isinstance(value, kind) or (isinstance(value, str) and not value.strip()):
        raise ConfigError(f"{where}: '{key}' is required and must be a {kind.__name__}")
    return value


def _coordinate(data: dict[str, Any], key: str, where: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{where}: '{key}' must be a number")
    return float(value)


def _parse_office(raw: dict[str, Any]) -> Office:
    timezone = raw.get("timezone", "Europe/Stockholm")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as err:
        raise ConfigError(f"office: unknown timezone '{timezone}'") from err
    radius = raw.get("radius_m", 500)
    if not isinstance(radius, int) or radius <= 0:
        raise ConfigError("office: 'radius_m' must be a positive integer")
    return Office(
        name=_require(raw, "name", str, "office"),
        address=_require(raw, "address", str, "office"),
        lat=_coordinate(raw, "lat", "office"),
        lon=_coordinate(raw, "lon", "office"),
        radius_m=radius,
        timezone=timezone,
    )


def _parse_restaurant(raw: Any, index: int) -> Restaurant:
    if not isinstance(raw, dict):
        raise ConfigError(f"restaurants[{index}] must be a mapping")
    rid = _require(raw, "id", str, f"restaurants[{index}]")
    where = f"restaurant '{rid}'"
    return Restaurant(
        id=rid,
        name=_require(raw, "name", str, where),
        lat=_coordinate(raw, "lat", where),
        lon=_coordinate(raw, "lon", where),
        address=str(raw.get("address", "")),
        hours=str(raw.get("hours", "")),
        includes=str(raw.get("includes", "")),
        menu_source=str(raw.get("menu_source", "")),
        favourite=bool(raw.get("favourite", False)),
        note=str(raw.get("note", "")),
        source=_parse_source(raw.get("source"), where),
    )


def _parse_source(raw: Any, where: str) -> SourceConfig | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: 'source' must be a mapping with type and url")
    source_type = raw.get("type")
    if source_type not in SOURCE_TYPES:
        raise ConfigError(f"{where}: source type must be one of {', '.join(SOURCE_TYPES)}")
    url = _require(raw, "url", str, f"{where} source")
    if not url.startswith(("https://", "http://")):
        raise ConfigError(f"{where}: source url must start with https://")
    dishes = tuple(_parse_static_dish(d, where) for d in raw.get("dishes") or [])
    if source_type == "static" and not dishes:
        raise ConfigError(f"{where}: a static source needs at least one dish")
    return SourceConfig(type=source_type, url=url, dishes=dishes)


def _parse_static_dish(raw: Any, where: str) -> Dish:
    if not isinstance(raw, dict):
        raise ConfigError(f"{where}: each static dish must be a mapping")
    kind = raw.get("kind", "other")
    if kind not in KINDS:
        raise ConfigError(f"{where}: dish kind must be one of {', '.join(KINDS)}")
    price = raw.get("price")
    if price is not None and (isinstance(price, bool) or not isinstance(price, int)):
        raise ConfigError(f"{where}: dish price must be a whole number of kronor")
    return Dish(
        name=clean_text(_require(raw, "name", str, f"{where} dish")),
        desc=clean_text(str(raw.get("desc", ""))),
        kind=kind,
        price=price,
    )
