"""Pure helpers that turn scraped strings into contract values: clean text, prices, dish kinds, dates.

No network or file I/O here (CLAUDE.md: normalize.py is data in, data out).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from scraper.models import Kind

_WHITESPACE = re.compile(r"\s+")
_PRICE = re.compile(r"(\d{2,4})(?:[.,]\d{1,2})?\s*(?:kr|sek|:-)?", re.IGNORECASE)

SWEDISH_MONTHS = {
    "januari": 1, "februari": 2, "mars": 3, "april": 4, "maj": 5, "juni": 6,
    "juli": 7, "augusti": 8, "september": 9, "oktober": 10, "november": 11, "december": 12,
}  # fmt: skip

# Keyword stems per kind, matched against lower-cased text. Swedish builds compounds
# ("lunchbuffé", "gravlax", "falukorv", "högrevsburgare"), so stems match anywhere in a word,
# except those listed in _WORD_START_ONLY, which are short enough to hide inside unrelated words
# ("räk" in "träkolsgrillad"). A dish is classified from its name first and its description
# second; when one text hits several kinds (e.g. "choose chicken or tofu") it is "other".
_KIND_KEYWORDS: dict[Kind, tuple[str, ...]] = {
    "buffet": ("buffé", "buffe", "buffet", "all you can eat", "all-you-can-eat"),
    "fish": (
        "fisk", "lax", "torsk", "sej", "kolja", "spätta", "makrill", "sill", "strömming", "gös",
        "abborre", "hälleflundra", "kummel", "lubb", "tonfisk", "räk", "skaldjur", "mussl", "krabba",
        "hummer", "sushi", "sashimi", "fish", "salmon", "tuna", "shrimp", "prawn", "seafood",
    ),
    "veg": (
        "vegetar", "vegan", "veggie", "halloumi", "falafel", "tofu", "linsgryta", "bönbiff",
        "grönsaksbiff", "vegobiff", "sojafärs", "vegofärs", "quorn",
    ),
    "meat": (
        "kött", "biff", "fläsk", "kyckling", "högrev", "oxfilé", "entrecote", "entrecôte",
        "burgare", "burger", "korv", "bacon", "lamm", "kalv", "skinka", "schnitzel", "sirloin",
        "carpaccio", "salsiccia", "chorizo", "anka", "kalkon", "hjort", "älg", "renskav",
        "wallenbergare", "kåldolm", "isterband", "pulled pork", "chicken", "beef", "pork", "steak",
        "mixed grill", "pastrami", "kebab", "gyros", "yakiniku", "carbonara", "guanciale",
        "mortadella", "prosciutto", "salami", "pancetta", "bulgogi",
    ),
}  # fmt: skip
_WORD_START_ONLY = {"sej", "sill", "gös", "räk", "lubb", "tuna", "anka", "älg", "lamm", "kalv"}
# Vegetarian compounds that contain a meat word ("bönbiff" contains "biff") are removed before
# looking for meat, so they do not turn a vegetarian dish into "other".
_VEG_COMPOUNDS = ("bönbiff", "grönsaksbiff", "vegobiff", "sojafärs", "vegofärs")


def _pattern(stem: str) -> re.Pattern[str]:
    prefix = r"(?<![a-zåäöéü])" if stem in _WORD_START_ONLY else ""
    return re.compile(prefix + re.escape(stem))


_KIND_PATTERNS = {kind: [_pattern(s) for s in stems] for kind, stems in _KIND_KEYWORDS.items()}


def clean_text(value: str | None) -> str:
    """Normalises unicode and collapses whitespace; None becomes an empty string."""
    if not value:
        return ""
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", value)).strip()


def parse_price(value: str | int | float | None) -> int | None:
    """'185', '109Kr', '129 kr', 145.0 -> whole kronor; anything without a plausible price -> None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    match = _PRICE.search(value)
    return int(match.group(1)) if match else None


def _kinds_in(text: str) -> set[Kind]:
    lowered = text.lower()
    without_veg_compounds = lowered
    for compound in _VEG_COMPOUNDS:
        without_veg_compounds = without_veg_compounds.replace(compound, " ")
    found: set[Kind] = set()
    for kind, patterns in _KIND_PATTERNS.items():
        haystack = lowered if kind == "veg" else without_veg_compounds
        if any(p.search(haystack) for p in patterns):
            found.add(kind)
    return found


def classify_dish(name: str, desc: str = "", vegetarian: bool = False) -> Kind:
    """Best-effort dish kind from Swedish/English menu text. `vegetarian` is a structured hint."""
    combined = _kinds_in(name + " " + desc)
    if "buffet" in combined:
        return "buffet"
    if vegetarian:
        return "veg"
    for text in (name, desc):
        found = _kinds_in(text) - {"buffet"}
        if len(found) > 1:
            return "other"
        if found:
            kind = found.pop()
            # Never call a dish vegetarian when meat or fish is mentioned anywhere in it.
            if kind == "veg" and combined & {"meat", "fish"}:
                return "other"
            return kind
    return "other"


def parse_swedish_day(label: str, year: int) -> date | None:
    """'Torsdag 5 november' (menydags section name) -> date(year, 11, 5); unknown format -> None."""
    match = re.search(r"(\d{1,2})\s+([a-zåäö]+)", label.lower())
    if not match or match.group(2) not in SWEDISH_MONTHS:
        return None
    try:
        return date(year, SWEDISH_MONTHS[match.group(2)], int(match.group(1)))
    except ValueError:
        return None
