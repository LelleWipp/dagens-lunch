"""Data model and the JSON contract with the frontend (see "JSON-kontraktet" in CLAUDE.md).

The to_json() methods are the only place the menus.json shape is defined in Python. If the
contract changes, update docs/app.js and tests/test_build.py in the same commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Literal

Kind = Literal["meat", "fish", "veg", "buffet", "other"]
Status = Literal["today", "standing", "link", "none", "error"]

KINDS: tuple[Kind, ...] = ("meat", "fish", "veg", "buffet", "other")
STATUSES: tuple[Status, ...] = ("today", "standing", "link", "none", "error")


@dataclass(frozen=True)
class Dish:
    name: str
    kind: Kind = "other"
    desc: str = ""
    price: int | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"name": self.name}
        if self.desc:
            out["desc"] = self.desc
        out["kind"] = self.kind
        if self.price is not None:
            out["price"] = self.price
        return out


@dataclass(frozen=True)
class SourceConfig:
    """Where a restaurant's menu comes from. `type` selects a module in scraper/sources/."""

    type: str
    url: str
    dishes: tuple[Dish, ...] = ()


@dataclass(frozen=True)
class Office:
    name: str
    address: str
    lat: float
    lon: float
    radius_m: int
    timezone: str


@dataclass(frozen=True)
class Restaurant:
    id: str
    name: str
    lat: float
    lon: float
    address: str = ""
    hours: str = ""
    includes: str = ""
    menu_source: str = ""
    favourite: bool = False
    note: str = ""
    source: SourceConfig | None = None

    def to_json(self, distance_m: int) -> dict[str, Any]:
        out: dict[str, Any] = {"id": self.id, "name": self.name}
        for key in ("address", "hours", "includes", "menu_source", "note"):
            value = getattr(self, key)
            if value:
                out[key] = value
        if self.favourite:
            out["favourite"] = True
        out["distance_m"] = distance_m
        return out


@dataclass(frozen=True)
class MenuEntry:
    status: Status
    dishes: tuple[Dish, ...] = ()
    note: str = ""
    source: str = ""

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"status": self.status, "dishes": [d.to_json() for d in self.dishes]}
        if self.note:
            out["note"] = self.note
        if self.source:
            out["source"] = self.source
        return out


@dataclass(frozen=True)
class Config:
    office: Office
    walk_speed_m_per_min: int
    restaurants: tuple[Restaurant, ...]


@dataclass(frozen=True)
class DailyMenu:
    day: date
    updated_at: datetime
    office: Office
    walk_speed_m_per_min: int
    restaurants: tuple[tuple[Restaurant, int], ...]  # (restaurant, distance_m)
    items: dict[str, MenuEntry] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        return {
            "date": self.day.isoformat(),
            "updated_at": self.updated_at.isoformat(timespec="seconds"),
            "office": {
                "name": self.office.name,
                "address": self.office.address,
                "radius_m": self.office.radius_m,
            },
            "walk_speed_m_per_min": self.walk_speed_m_per_min,
            "restaurants": [r.to_json(distance) for r, distance in self.restaurants],
            "items": {rid: entry.to_json() for rid, entry in self.items.items()},
        }
