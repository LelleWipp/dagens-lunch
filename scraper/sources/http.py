"""The one place the scraper talks to the network: a polite HTTP client that honours robots.txt.

CLAUDE.md: one request per restaurant and day, a clear User-Agent, follow robots.txt.
"""

from __future__ import annotations

import os
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from scraper.sources.base import SourceError

TIMEOUT_S = 20.0


def user_agent() -> str:
    # GITHUB_REPOSITORY is set in Actions, so a fork identifies itself with its own repo URL.
    repo = os.environ.get("GITHUB_REPOSITORY", "LelleWipp/dagens-lunch")
    return f"dagens-lunch/1.0 (+https://github.com/{repo}; one request per restaurant per weekday)"


class PoliteClient:
    """httpx client that checks robots.txt once per host before fetching a page."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            headers={"User-Agent": user_agent(), "Accept-Language": "sv-SE,sv;q=0.9"},
            timeout=TIMEOUT_S,
            follow_redirects=True,
        )
        self._robots: dict[str, RobotFileParser] = {}

    def get_text(self, url: str) -> str:
        if not self._allowed(url):
            raise SourceError(f"robots.txt disallows {url}")
        try:
            response = self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as err:
            raise SourceError(f"GET {url} failed: {err}") from err
        return response.text

    def _allowed(self, url: str) -> bool:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._robots:
            self._robots[origin] = self._load_robots(origin)
        return self._robots[origin].can_fetch(user_agent(), url)

    def _load_robots(self, origin: str) -> RobotFileParser:
        parser = RobotFileParser()
        try:
            response = self._client.get(origin + "/robots.txt")
        except httpx.HTTPError as err:
            raise SourceError(f"could not read {origin}/robots.txt: {err}") from err
        if response.status_code >= 400:
            parser.parse([])  # no robots.txt (4xx) means everything is allowed
        else:
            parser.parse(response.text.splitlines())
        return parser

    def close(self) -> None:
        self._client.close()
