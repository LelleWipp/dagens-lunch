import httpx
import pytest

from scraper.sources.base import SourceError
from scraper.sources.http import PoliteClient, user_agent

pytestmark = pytest.mark.skipif(not hasattr(httpx, "MockTransport"), reason="needs real httpx")


def client_for(handler):
    return PoliteClient(httpx.Client(transport=httpx.MockTransport(handler)))


def test_respects_robots_txt():
    seen = []

    def handler(request):
        seen.append(request.url.path)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private/\n")
        return httpx.Response(200, text="<html>ok</html>")

    client = client_for(handler)
    assert client.get_text("https://site.example/menu") == "<html>ok</html>"
    with pytest.raises(SourceError, match=r"robots\.txt"):
        client.get_text("https://site.example/private/menu")
    client.get_text("https://site.example/other")
    assert seen.count("/robots.txt") == 1  # fetched once per host
    assert "/private/menu" not in seen


def test_missing_robots_txt_allows_everything():
    client = client_for(
        lambda r: httpx.Response(404) if r.url.path == "/robots.txt" else httpx.Response(200, text="ok")
    )
    assert client.get_text("https://site.example/menu") == "ok"


def test_http_error_becomes_source_error():
    client = client_for(
        lambda r: httpx.Response(200, text="") if r.url.path == "/robots.txt" else httpx.Response(503)
    )
    with pytest.raises(SourceError, match="503"):
        client.get_text("https://site.example/menu")


def test_user_agent_names_the_repo(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "someone/their-fork")
    assert "github.com/someone/their-fork" in user_agent()
