"""Normalisation and enrichment utilities."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from numbers import Number
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:  # Optional dependency for flexible timestamp parsing.
    from dateutil import parser as dateparser  # type: ignore
except ImportError:  # pragma: no cover - environment without python-dateutil
    dateparser = None  # type: ignore

from email.utils import parsedate_to_datetime

from .models import NormalisedSignal, RawSignal


URL_RE = re.compile(r"https?://[^\s)]+", re.I)


def norm_text(*parts: str) -> str:
    return re.sub(r"\s+", " ", " ".join(filter(None, parts))).strip()


def to_utc(value) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, Number):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    else:
        dt = None
        if dateparser is not None:
            try:
                dt = dateparser.parse(str(value))
            except Exception:  # pragma: no cover - parser failure fallback
                dt = None
        if dt is None:
            try:
                dt = parsedate_to_datetime(str(value))
            except Exception:  # pragma: no cover - fallback to now
                dt = None
    if dt is None:
        dt = datetime.now(timezone.utc)
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def extract_urls(text: str) -> List[str]:
    return [match.group(0) for match in URL_RE.finditer(text or "")]


def keyword_score(
    text: str,
    keywords: Dict[str, float],
    code_names: Dict[str, float],
    negatives: Sequence[str],
) -> Tuple[float, List[str], bool]:
    haystack = text.lower()
    matches: List[str] = []
    score = 0.0
    for word, weight in keywords.items():
        if word in haystack:
            matches.append(word)
            score += float(weight)
    for word, weight in code_names.items():
        if word in haystack:
            matches.append(word)
            score += float(weight)
    negative_flag = any(neg in haystack for neg in negatives)
    if negative_flag:
        score *= 0.5
    return min(score / 10.0, 1.0), matches, negative_flag


def detect_zone(text: str, zones: Dict[str, Dict[str, float]]) -> Tuple[Optional[str], Optional[Tuple[float, float]]]:
    lowered = text.lower()
    for name, coords in zones.items():
        if name in lowered:
            lat = coords.get("lat")
            lon = coords.get("lon")
            if lat is None or lon is None:
                continue
            return name, (float(lat), float(lon))
    return None, None


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()


def normalise(
    raw: RawSignal,
    keywords: Dict[str, float],
    code_names: Dict[str, float],
    negatives: Sequence[str],
    zones: Dict[str, Dict[str, float]],
) -> NormalisedSignal:
    payload = raw.payload
    title = payload.get("title", "")
    summary = payload.get("summary", "")
    text = norm_text(title, summary)
    timestamp = to_utc(payload.get("published"))
    urls = extract_urls(" ".join([text, payload.get("link", "")]))
    zone_name, coords = detect_zone(text, zones)
    kw_score, signals, negative_flag = keyword_score(text, keywords, code_names, negatives)

    unique_basis = "|".join(
        [raw.source, payload.get("link", ""), title, timestamp.isoformat()]
    )
    identifier = sha1(unique_basis)

    return NormalisedSignal(
        id=identifier,
        source=raw.source,
        author=payload.get("author"),
        title=title,
        text=text,
        timestamp_utc=timestamp,
        urls=urls,
        place=zone_name,
        latlon=coords,
        signals=signals,
        negative_flag=negative_flag,
        extra={
            "raw_link": payload.get("link", ""),
            "raw_id": payload.get("id", ""),
            "kw_component": kw_score,
        },
    )
