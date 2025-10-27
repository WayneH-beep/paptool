import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from paptool.models import NormalisedSignal, RawSignal
from paptool.normalizer import normalise
from paptool.scoring import score_signals
from paptool.pipeline import run_pipeline
from paptool.config import Config
from paptool.connectors.base import BaseConnector


class StubConnector(BaseConnector):
    def __init__(self, name, signals):
        super().__init__(name)
        self._signals = signals

    async def fetch(self):
        return list(self._signals)


def test_normalise_detects_keywords_and_zones():
    raw = RawSignal(
        source="rss",
        payload={
            "title": "Unit base spotted",
            "summary": "Camden lock TTRO https://council.example/notice.pdf for Dark Train student film",
            "published": datetime(2024, 1, 1, 12, tzinfo=timezone.utc),
            "link": "https://council.example/notice.pdf",
            "author": "Camden Council",
        },
    )
    keywords = {"unit base": 3.0}
    code_names = {"dark train": 2.0}
    negatives = ["student film"]
    zones = {"camden": {"lat": 51.545, "lon": -0.162}}

    signal = normalise(raw, keywords, code_names, negatives, zones)

    assert signal.signals == ["unit base", "dark train"]
    assert signal.negative_flag is True
    assert signal.extra["kw_component"] == pytest.approx(0.25)
    assert signal.place == "camden"
    assert signal.latlon == (51.545, -0.162)
    assert "https://council.example/notice.pdf" in signal.urls
    assert signal.timestamp_utc == datetime(2024, 1, 1, 12, tzinfo=timezone.utc)


def test_score_signals_combines_components():
    now = datetime.now(timezone.utc)
    signal = NormalisedSignal(
        id="1",
        source="rss",
        author="source",
        title="Test",
        text="Test",
        timestamp_utc=now - timedelta(hours=12),
        urls=[],
        place=None,
        latlon=(51.5, -0.1),
        signals=[],
        negative_flag=False,
        extra={"kw_component": 0.6, "source_cred": 0.7, "evidence": 0.2},
    )
    scoring_cfg = {
        "recency_half_life_hours": 24,
        "max_km_for_proximity": 100,
        "weights": {
            "recency": 0.4,
            "proximity": 0.3,
            "keywords": 0.2,
            "source_cred": 0.05,
            "evidence": 0.05,
        },
    }

    score_signals([signal], scoring_cfg, 51.5, -0.1)

    expected_recency = 0.5 ** (12 / 24)
    assert signal.score_breakdown.recency == pytest.approx(expected_recency)
    assert signal.score_breakdown.proximity == pytest.approx(1.0)
    expected_score = (
        expected_recency * 0.4
        + 1.0 * 0.3
        + 0.6 * 0.2
        + 0.7 * 0.05
        + 0.2 * 0.05
    )
    assert signal.score == pytest.approx(expected_score)


def test_run_pipeline_scores_and_deduplicates():
    published = datetime.now(timezone.utc) - timedelta(hours=2)
    base_payload = {
        "title": "Unit base in Camden",
        "published": published,
        "link": "https://council.gov.uk/notices/123",
        "author": "Camden",
    }
    low_payload = dict(base_payload)
    low_payload["summary"] = "Road works near unit base"

    high_payload = dict(base_payload)
    high_payload["summary"] = "Road closure TTRO notice https://council.gov.uk/notices/123.pdf"

    connector_low = StubConnector(
        "low",
        [RawSignal(source="rss", payload=low_payload)],
    )
    connector_high = StubConnector(
        "high",
        [RawSignal(source="rss", payload=high_payload)],
    )

    cfg = Config(
        {
            "vocabulary": {"keywords": {"unit base": 3.0}},
            "zones": {"camden": {"lat": 51.545, "lon": -0.162}},
            "scoring": {
                "recency_half_life_hours": 48,
                "max_km_for_proximity": 100,
                "weights": {
                    "recency": 0.5,
                    "proximity": 0.2,
                    "keywords": 0.2,
                    "source_cred": 0.05,
                    "evidence": 0.05,
                },
            },
            "home_base": {"lat": 51.545, "lon": -0.162},
            "source_weights": {"council.gov.uk": 0.9},
        }
    )

    result = asyncio.run(run_pipeline(cfg, [connector_low, connector_high]))

    assert len(result) == 1
    top = result[0]
    # Evidence term should boost the version with the TTRO link
    assert top.extra["evidence"] == pytest.approx(0.2)
    assert top.extra["source_cred"] == pytest.approx(0.9)
    assert top.signals == ["unit base"]
    assert top.place == "camden"
    assert top.latlon == (51.545, -0.162)
