"""Scoring helpers for normalised signals."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Dict, Iterable

from .models import NormalisedSignal, ScoreBreakdown


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def recency_component(published: datetime, half_life_h: float) -> float:
    age_h = (datetime.now(timezone.utc) - published).total_seconds() / 3600.0
    if age_h < 0:
        age_h = 0
    return max(0.0, 0.5 ** (age_h / max(half_life_h, 0.1)))


def proximity_component(item_latlon, home_lat, home_lon, max_km: float) -> float:
    if not item_latlon:
        return 0.0
    lat, lon = item_latlon
    km = haversine_km(lat, lon, home_lat, home_lon)
    if km >= max_km:
        return 0.0
    return 1.0 - (km / max_km)


def final_score(breakdown: ScoreBreakdown, weights: Dict[str, float]) -> float:
    return sum(getattr(breakdown, key, 0.0) * weights.get(key, 0.0) for key in weights.keys())


def score_signals(
    signals: Iterable[NormalisedSignal],
    scoring_cfg: Dict[str, float],
    home_lat: float,
    home_lon: float,
) -> None:
    weights = scoring_cfg.get("weights") or {
        "recency": 0.35,
        "proximity": 0.25,
        "keywords": 0.25,
        "source_cred": 0.1,
        "evidence": 0.05,
    }
    half_life = float(scoring_cfg.get("recency_half_life_hours", 24.0))
    max_km = float(scoring_cfg.get("max_km_for_proximity", 60.0))

    for signal in signals:
        extra = signal.extra or {}
        recency = recency_component(signal.timestamp_utc, half_life)
        proximity = proximity_component(signal.latlon, home_lat, home_lon, max_km)
        keywords = float(extra.get("kw_component", 0.0))
        source_cred = float(extra.get("source_cred", 0.4))
        evidence = float(extra.get("evidence", 0.0))
        breakdown = ScoreBreakdown(
            recency=recency,
            proximity=proximity,
            keywords=keywords,
            source_cred=source_cred,
            evidence=evidence,
        )
        signal.score_breakdown = breakdown
        signal.score = final_score(breakdown, weights)
