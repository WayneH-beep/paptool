"""Data models used throughout the Pap Signal Harvester pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass
class RawSignal:
    """A raw item produced by a connector before normalisation."""

    source: str
    payload: Dict[str, Any]


@dataclass
class ScoreBreakdown:
    """Components that contributed to the final score."""

    recency: float
    proximity: float
    keywords: float
    source_cred: float
    evidence: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "recency": self.recency,
            "proximity": self.proximity,
            "keywords": self.keywords,
            "source_cred": self.source_cred,
            "evidence": self.evidence,
        }


@dataclass
class NormalisedSignal:
    """A signal ready for scoring and persistence."""

    id: str
    source: str
    author: Optional[str]
    title: str
    text: str
    timestamp_utc: datetime
    urls: List[str]
    place: Optional[str]
    latlon: Optional[Tuple[float, float]]
    signals: List[str]
    negative_flag: bool
    extra: Dict[str, Any] = field(default_factory=dict)
    score_breakdown: Optional[ScoreBreakdown] = None
    score: float = 0.0

    def iter_output_rows(self, limit_fields: Optional[Sequence[str]] = None) -> Iterable[Dict[str, Any]]:
        """Yield dictionaries for CSV/DB output."""

        base = {
            "id": self.id,
            "source": self.source,
            "author": self.author or "",
            "title": self.title,
            "text": self.text,
            "published_utc": self.timestamp_utc.isoformat(),
            "urls": ", ".join(self.urls),
            "place": self.place or "",
            "lat": self.latlon[0] if self.latlon else "",
            "lon": self.latlon[1] if self.latlon else "",
            "signals": ", ".join(self.signals),
            "negative_flag": self.negative_flag,
            "score": f"{self.score:.3f}",
        }
        if self.score_breakdown:
            base.update({f"score_{k}": f"{v:.3f}" for k, v in self.score_breakdown.as_dict().items()})
        base.update(self.extra)

        if limit_fields:
            return [{field: base.get(field, "") for field in limit_fields}]
        return [base]
