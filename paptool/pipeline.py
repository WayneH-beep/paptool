"""Pipeline orchestration."""

from __future__ import annotations

import asyncio
import re
from typing import Iterable, List

from .config import Config
from .connectors import BaseConnector
from .models import NormalisedSignal, RawSignal
from .normalizer import normalise
from .scoring import score_signals


HOST_RE = re.compile(r"https?://([^/]+)/?", re.I)


def host_weight(link: str, source_weights) -> float:
    if not link:
        return 0.3
    match = HOST_RE.search(link)
    if not match:
        return 0.3
    host = match.group(1).lower()
    for key, value in source_weights.items():
        if key in host:
            return float(value)
    return 0.4


def evidence_score(text: str) -> float:
    return 0.2 if re.search(r"(ttro|order|notice|pdf|road\s+closure|permit)", text, re.I) else 0.0


async def gather_raw(connectors: Iterable[BaseConnector]) -> List[RawSignal]:
    tasks = [asyncio.create_task(connector.fetch()) for connector in connectors]
    results: List[RawSignal] = []
    for task in tasks:
        try:
            items = await task
            results.extend(items)
        except Exception as exc:  # pragma: no cover - logging only
            print(f"[!] Connector error: {exc}")
    return results


def dedupe(signals: List[NormalisedSignal]) -> List[NormalisedSignal]:
    deduped = {}
    for signal in signals:
        existing = deduped.get(signal.id)
        if not existing or existing.score < signal.score:
            deduped[signal.id] = signal
    return list(deduped.values())


async def run_pipeline(cfg: Config, connectors: Iterable[BaseConnector]) -> List[NormalisedSignal]:
    raw_signals = await gather_raw(connectors)

    vocab = cfg.vocabulary
    keywords = {k.lower(): float(v) for k, v in (vocab.get("keywords") or {}).items()}
    code_names = {k.lower(): float(v) for k, v in (vocab.get("code_names") or {}).items()}
    negatives = [s.lower() for s in (vocab.get("negative_keywords") or [])]
    zones = {k.lower(): v for k, v in (cfg.zones or {}).items()}

    normalised: List[NormalisedSignal] = []
    for raw in raw_signals:
        signal = normalise(raw, keywords, code_names, negatives, zones)
        signal.extra["source_cred"] = host_weight(signal.extra.get("raw_link"), cfg.source_weights)
        signal.extra["evidence"] = evidence_score(signal.text)
        normalised.append(signal)

    home = cfg.home_base or {}
    home_lat = float(home.get("lat", 51.5074))
    home_lon = float(home.get("lon", -0.1278))

    score_signals(normalised, cfg.scoring, home_lat, home_lon)
    deduped = dedupe(normalised)
    deduped.sort(key=lambda s: s.score, reverse=True)
    return deduped
