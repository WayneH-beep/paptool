"""Configuration helpers for the Pap Signal Harvester."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

try:  # Optional dependency for reading YAML configuration files.
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - environment without PyYAML
    yaml = None  # type: ignore


DEFAULT_CONFIG_YAML = """\
# pap_config.yaml — edit to your taste

home_base:
  name: "London"
  lat: 51.5074
  lon: -0.1278

connectors:
  rss:
    feeds:
      - "https://www.reddit.com/r/london/new/.rss"
      - "https://www.reddit.com/r/Filmmakers/new/.rss"
  reddit:
    enabled: false
    client_id: ""
    client_secret: ""
    user_agent: "pap-signal-harvester"
    subreddit: "filmmakers"
    keywords: []
  email:
    enabled: false
    imap_host: "imap.example.com"
    username: "pap@example.com"
    password_env: "PAP_IMAP_PASSWORD"

vocabulary:
  keywords:
    "unit base": 3.0
    "basecamp": 3.0
    "lock-off": 2.5
    "road closure": 2.0
    "ttro": 2.5
    "filming": 2.0
    "film crew": 2.0
    "location permit": 1.5
    "tech recce": 1.2
    "wardrobe truck": 1.0
    "lighting trucks": 1.0
  code_names:
    "plum jam productions": 3.0
    "dark train": 3.0
    "magic roundabout": 3.0
    "mirage pictures": 2.5
    "planit films": 2.5
    "berrybushes": 2.0
  negative_keywords:
    - "student film"
    - "wedding"
    - "birthday party"
    - "private hire"

zones:
  "lustleigh": { lat: 50.596, lon: -3.722 }
  "windsor": { lat: 51.483, lon: -0.604 }
  "windsor great park": { lat: 51.425, lon: -0.604 }
  "leavesden": { lat: 51.691, lon: -0.417 }
  "shepperton": { lat: 51.410, lon: -0.449 }
  "pinewood": { lat: 51.548, lon: -0.536 }
  "longcross": { lat: 51.386, lon: -0.575 }
  "camden": { lat: 51.545, lon: -0.162 }
  "westminster": { lat: 51.500, lon: -0.126 }
  "greenwich": { lat: 51.482, lon: 0.007 }
  "watford": { lat: 51.657, lon: -0.392 }
  "watford borough": { lat: 51.657, lon: -0.392 }
  "surrey": { lat: 51.271, lon: -0.341 }
  "kent": { lat: 51.278, lon: 0.521 }
  "essex": { lat: 51.736, lon: 0.470 }
  "berrybushes": { lat: 51.683, lon: -0.417 }

scoring:
  recency_half_life_hours: 24
  max_km_for_proximity: 60
  weights:
    recency: 0.35
    proximity: 0.25
    keywords: 0.2
    source_cred: 0.15
    evidence: 0.05

source_weights:
  "reddit.com": 0.5
  "one.network": 0.8
  "gov.uk": 1.0
  "london.gov.uk": 0.9
  "filmoffice.co.uk": 0.8
  "studios": 0.8

output:
  csv_path: "./signals.csv"
  markdown_path: "./signals.md"
  max_rows: 200
  console_limit: 30

storage:
  kind: "postgres"
  dsn: "postgresql://pap:pappassword@localhost:5432/papsignals"
  create_schema: false
"""


@dataclass
class Config:
    raw: Dict[str, Any]

    @property
    def connectors(self) -> Dict[str, Any]:
        return self.raw.get("connectors", {})

    @property
    def vocabulary(self) -> Dict[str, Any]:
        return self.raw.get("vocabulary", {})

    @property
    def zones(self) -> Dict[str, Any]:
        return self.raw.get("zones", {})

    @property
    def scoring(self) -> Dict[str, Any]:
        return self.raw.get("scoring", {})

    @property
    def output(self) -> Dict[str, Any]:
        return self.raw.get("output", {})

    @property
    def storage(self) -> Dict[str, Any]:
        return self.raw.get("storage", {})

    @property
    def source_weights(self) -> Dict[str, float]:
        return {k.lower(): float(v) for k, v in (self.raw.get("source_weights") or {}).items()}

    @property
    def home_base(self) -> Dict[str, Any]:
        return self.raw.get("home_base", {})


def ensure_config(path: str = "./pap_config.yaml") -> Config:
    cfg_path = Path(path)
    if not cfg_path.exists():
        cfg_path.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")
        print(f"[i] Created default config at {path}. Edit it and run again.")
        raise SystemExit(0)
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required to load configuration files. Install it with `pip install pyyaml`."
        )
    with cfg_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return Config(data)


def env_or_default(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    if value.startswith("env:"):
        _, env_name = value.split(":", 1)
        return os.environ.get(env_name.strip())
    return value
