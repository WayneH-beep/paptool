"""PostgreSQL persistence for harvested signals."""

from __future__ import annotations

from typing import Iterable

try:  # pragma: no cover - optional dependency
    import psycopg
except ImportError:  # pragma: no cover - optional dependency
    psycopg = None

from ..models import NormalisedSignal

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS signal_sources (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    source_id INTEGER REFERENCES signal_sources(id),
    author TEXT,
    title TEXT,
    body TEXT,
    harvested_at TIMESTAMPTZ DEFAULT NOW(),
    signal_time TIMESTAMPTZ,
    urls TEXT,
    place TEXT,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION,
    signals TEXT,
    negative_flag BOOLEAN,
    score DOUBLE PRECISION,
    score_recency DOUBLE PRECISION,
    score_proximity DOUBLE PRECISION,
    score_keywords DOUBLE PRECISION,
    score_source_cred DOUBLE PRECISION,
    score_evidence DOUBLE PRECISION
);
"""


class PostgresStorage:  # pragma: no cover - requires external DB
    def __init__(self, dsn: str, create_schema: bool = False) -> None:
        if not dsn:
            raise ValueError("Postgres DSN must be provided")
        if psycopg is None:
            raise RuntimeError("psycopg is not installed. Install psycopg[binary] to enable Postgres storage.")
        self.dsn = dsn
        self.create_schema = create_schema
        if create_schema:
            self.ensure_schema()

    def ensure_schema(self) -> None:
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            conn.execute(SCHEMA_SQL)

    def persist(self, signals: Iterable[NormalisedSignal]) -> None:
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                for signal in signals:
                    cur.execute(
                        "INSERT INTO signal_sources(name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                        (signal.source,),
                    )
                    source_id = cur.fetchone()[0]
                    cur.execute(
                        """
                        INSERT INTO signals (
                            id, source_id, author, title, body, signal_time, urls, place,
                            lat, lon, signals, negative_flag, score, score_recency, score_proximity,
                            score_keywords, score_source_cred, score_evidence
                        ) VALUES (
                            %(id)s, %(source_id)s, %(author)s, %(title)s, %(body)s, %(signal_time)s, %(urls)s, %(place)s,
                            %(lat)s, %(lon)s, %(signals)s, %(negative_flag)s, %(score)s,
                            %(score_recency)s, %(score_proximity)s, %(score_keywords)s,
                            %(score_source_cred)s, %(score_evidence)s
                        ) ON CONFLICT (id) DO UPDATE SET
                            source_id = EXCLUDED.source_id,
                            author = EXCLUDED.author,
                            title = EXCLUDED.title,
                            body = EXCLUDED.body,
                            signal_time = EXCLUDED.signal_time,
                            urls = EXCLUDED.urls,
                            place = EXCLUDED.place,
                            lat = EXCLUDED.lat,
                            lon = EXCLUDED.lon,
                            signals = EXCLUDED.signals,
                            negative_flag = EXCLUDED.negative_flag,
                            score = EXCLUDED.score,
                            score_recency = EXCLUDED.score_recency,
                            score_proximity = EXCLUDED.score_proximity,
                            score_keywords = EXCLUDED.score_keywords,
                            score_source_cred = EXCLUDED.score_source_cred,
                            score_evidence = EXCLUDED.score_evidence
                        """,
                        {
                            "id": signal.id,
                            "source_id": source_id,
                            "author": signal.author,
                            "title": signal.title,
                            "body": signal.text,
                            "signal_time": signal.timestamp_utc,
                            "urls": ", ".join(signal.urls),
                            "place": signal.place,
                            "lat": signal.latlon[0] if signal.latlon else None,
                            "lon": signal.latlon[1] if signal.latlon else None,
                            "signals": ", ".join(signal.signals),
                            "negative_flag": signal.negative_flag,
                            "score": signal.score,
                            "score_recency": signal.score_breakdown.recency if signal.score_breakdown else None,
                            "score_proximity": signal.score_breakdown.proximity if signal.score_breakdown else None,
                            "score_keywords": signal.score_breakdown.keywords if signal.score_breakdown else None,
                            "score_source_cred": signal.score_breakdown.source_cred if signal.score_breakdown else None,
                            "score_evidence": signal.score_breakdown.evidence if signal.score_breakdown else None,
                        },
                    )
            conn.commit()
