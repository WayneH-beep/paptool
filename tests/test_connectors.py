import asyncio

from paptool.connectors import rss


class DummyResponse:
    def __init__(self, payload: str):
        self._payload = payload.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._payload


def test_rss_connector_stdlib_fallback(monkeypatch):
    feed_xml = """<?xml version='1.0'?>
    <rss version='2.0'>
      <channel>
        <title>Pap Feed</title>
        <item>
          <title>Unit base in Camden</title>
          <description>Road closure TTRO notice</description>
          <link>https://council.example/notices/123</link>
          <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
          <author>Camden Council</author>
        </item>
      </channel>
    </rss>
    """

    monkeypatch.setattr(rss, "feedparser", None)
    monkeypatch.setattr(rss, "urlopen", lambda url: DummyResponse(feed_xml))

    connector = rss.RSSConnector("https://council.example/feed")
    signals = asyncio.run(connector.fetch())

    assert len(signals) == 1
    signal = signals[0]
    assert signal.payload["title"] == "Unit base in Camden"
    assert signal.payload["link"] == "https://council.example/notices/123"
    assert signal.payload["author"] == "Camden Council"
    assert signal.payload["published"]
