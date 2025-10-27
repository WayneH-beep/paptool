"""Connector factory and exports."""

from __future__ import annotations

from typing import Iterable, List

from .base import BaseConnector

try:  # Optional dependency: feedparser
    from .rss import RSSConnector
except ImportError:  # pragma: no cover - environment without feedparser
    RSSConnector = None  # type: ignore

try:  # Optional dependency: praw
    from .reddit import RedditConnector
except ImportError:  # pragma: no cover - environment without praw
    RedditConnector = None  # type: ignore

try:  # Optional dependency: imapclient
    from .email_imap import EmailConnector
except ImportError:  # pragma: no cover - environment without imapclient
    EmailConnector = None  # type: ignore

__all__ = [
    "BaseConnector",
    "RSSConnector",
    "RedditConnector",
    "EmailConnector",
    "build_connectors",
]


def build_connectors(cfg) -> List[BaseConnector]:
    connectors_cfg = cfg.connectors
    connectors: List[BaseConnector] = []

    rss_cfg = connectors_cfg.get("rss") or {}
    for feed_url in rss_cfg.get("feeds", []) or []:
        if RSSConnector is None:
            raise RuntimeError(
                "feedparser is required for RSS connectors. Install it with `pip install feedparser`."
            )
        connectors.append(RSSConnector(feed_url))

    reddit_cfg = connectors_cfg.get("reddit") or {}
    if reddit_cfg.get("enabled"):
        if RedditConnector is None:
            raise RuntimeError(
                "praw is required for the Reddit connector. Install it with `pip install praw`."
            )
        connectors.append(
            RedditConnector(
                client_id=reddit_cfg.get("client_id"),
                client_secret=reddit_cfg.get("client_secret"),
                user_agent=reddit_cfg.get("user_agent", "pap-signal-harvester"),
                subreddit=reddit_cfg.get("subreddit", "filmmakers"),
                keywords=reddit_cfg.get("keywords") or [],
            )
        )

    email_cfg = connectors_cfg.get("email") or {}
    if email_cfg.get("enabled"):
        if EmailConnector is None:
            raise RuntimeError(
                "imapclient is required for the email connector. Install it with `pip install imapclient`."
            )
        connectors.append(
            EmailConnector(
                host=email_cfg.get("imap_host"),
                username=email_cfg.get("username"),
                password_env=email_cfg.get("password_env"),
            )
        )

    return connectors
