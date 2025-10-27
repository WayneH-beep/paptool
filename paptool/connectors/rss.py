"""Connector for RSS/Atom feeds using feedparser."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import feedparser

from ..models import RawSignal
from .base import BaseConnector


class RSSConnector(BaseConnector):
    """Fetch entries from a single RSS/Atom feed."""

    def __init__(self, feed_url: str):
        super().__init__(name=f"rss:{feed_url}")
        self.feed_url = feed_url

    def _parse_feed(self) -> List[RawSignal]:
        parsed = feedparser.parse(self.feed_url)
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

    async def fetch(self) -> List[RawSignal]:
        return await self._run_in_executor(self._parse_feed)
