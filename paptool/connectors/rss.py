"""Connector for RSS/Atom feeds."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List
from urllib.request import urlopen
from xml.etree import ElementTree as ET

try:  # Optional dependency offering rich feed parsing.
    import feedparser  # type: ignore
except ImportError:  # pragma: no cover - environment without feedparser
    feedparser = None  # type: ignore

from ..models import RawSignal
from .base import BaseConnector


def _iter_elements(entry, names: Iterable[str]):
    lowered = {name.lower() for name in names}
    for element in entry.iter():
        local = element.tag.split("}")[-1].lower()
        if local in lowered:
            yield element


def _first_text(entry, names: Iterable[str]) -> str:
    for element in _iter_elements(entry, names):
        text = (element.text or "").strip()
        if text:
            return text
        # Some Atom feeds nest author/name.
        for child in element:
            text = (child.text or "").strip()
            if text:
                return text
    return ""


def _first_link(entry) -> str:
    for element in _iter_elements(entry, ["link", "id"]):
        href = element.attrib.get("href")
        if href:
            return href.strip()
        text = (element.text or "").strip()
        if text:
            return text
    return ""


class RSSConnector(BaseConnector):
    """Fetch entries from a single RSS/Atom feed."""

    def __init__(self, feed_url: str):
        super().__init__(name=f"rss:{feed_url}")
        self.feed_url = feed_url

    def _parse_with_feedparser(self) -> List[RawSignal]:
        parsed = feedparser.parse(self.feed_url)  # type: ignore[arg-type]
        signals: List[RawSignal] = []
        for entry in parsed.entries:
            payload = {
                "title": entry.get("title", ""),
                "summary": entry.get("summary", "") or entry.get("description", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", "") or entry.get("updated", ""),
                "author": entry.get("author", ""),
            }
            if payload["published"]:
                published = payload["published"]
            else:
                published = datetime.now(timezone.utc).isoformat()
            payload["published"] = published
            signals.append(RawSignal(source=self.feed_url, payload=payload))
        return signals

    def _parse_with_stdlib(self) -> List[RawSignal]:
        signals: List[RawSignal] = []
        try:
            with urlopen(self.feed_url) as response:
                content = response.read()
        except Exception as exc:  # pragma: no cover - network error logging
            print(f"[!] RSS fetch failed for {self.feed_url}: {exc}")
            return signals

        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:  # pragma: no cover - malformed feed
            print(f"[!] RSS parse error for {self.feed_url}: {exc}")
            return signals

        entries = list(root.findall(".//item"))
        if not entries:
            entries = list(root.findall(".//{http://www.w3.org/2005/Atom}entry"))

        for entry in entries:
            title = _first_text(entry, ["title"])
            summary = _first_text(entry, ["summary", "description", "content", "content:encoded"])
            link = _first_link(entry)
            published = _first_text(entry, ["published", "updated", "pubDate", "date"])
            author = _first_text(entry, ["author", "name", "creator"])

            if not published:
                published = datetime.now(timezone.utc).isoformat()

            payload = {
                "title": title,
                "summary": summary,
                "link": link,
                "published": published,
                "author": author,
            }
            signals.append(RawSignal(source=self.feed_url, payload=payload))

        return signals

    def _parse_feed(self) -> List[RawSignal]:
        if feedparser is not None:
            return self._parse_with_feedparser()
        return self._parse_with_stdlib()

    async def fetch(self) -> List[RawSignal]:
        return await self._run_in_executor(self._parse_feed)
