"""Connector for Reddit using the praw API."""

from __future__ import annotations

from typing import List, Sequence

try:
    import praw
except ImportError:  # pragma: no cover - optional dependency
    praw = None

from ..models import RawSignal
from .base import BaseConnector


class RedditConnector(BaseConnector):
    """Poll a subreddit for recent submissions containing keywords."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str,
        subreddit: str,
        keywords: Sequence[str],
        limit: int = 50,
    ) -> None:
        super().__init__(name=f"reddit:{subreddit}")
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.subreddit = subreddit
        self.keywords = [k.lower() for k in keywords]
        self.limit = limit

    def _iter_submissions(self) -> List[RawSignal]:  # pragma: no cover - network call
        if praw is None:
            raise RuntimeError("praw is not installed. Install praw to enable Reddit ingestion.")
        reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
        )
        subreddit = reddit.subreddit(self.subreddit)
        results: List[RawSignal] = []
        for submission in subreddit.new(limit=self.limit):
            text_blob = " ".join(filter(None, [submission.title or "", submission.selftext or ""]))
            if self.keywords and not any(k in text_blob.lower() for k in self.keywords):
                continue
            payload = {
                "title": submission.title,
                "summary": submission.selftext or "",
                "link": submission.url,
                "published": submission.created_utc,
                "author": getattr(submission.author, "name", ""),
                "id": submission.id,
            }
            results.append(RawSignal(source=f"reddit:{self.subreddit}", payload=payload))
        return results

    async def fetch(self) -> List[RawSignal]:  # pragma: no cover - network call
        return await self._run_in_executor(self._iter_submissions)
