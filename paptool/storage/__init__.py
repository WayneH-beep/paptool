"""Storage helpers."""

from __future__ import annotations

from typing import Iterable

from ..models import NormalisedSignal
from .postgres import PostgresStorage


__all__ = ["create_storage", "PostgresStorage"]


def create_storage(cfg):
    storage_cfg = cfg.storage or {}
    kind = (storage_cfg.get("kind") or "").lower()
    if kind == "postgres":
        return PostgresStorage(storage_cfg.get("dsn"), create_schema=storage_cfg.get("create_schema", False))
    return None


def persist(storage, signals: Iterable[NormalisedSignal]) -> None:
    if storage is None:
        return
    storage.persist(signals)
