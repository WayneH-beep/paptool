"""Output helpers for CSV/Markdown and console tables."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from .models import NormalisedSignal


def _escape_markdown_cell(value: str) -> str:
    text = str(value or "")
    text = text.replace("\n", " ")
    return text.replace("|", "\\|")


def write_csv(path: str, signals: Sequence[NormalisedSignal], fieldnames=None) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with path_obj.open("w", encoding="utf-8", newline="") as handle:
        if fieldnames is None:
            fieldnames = [
                "score",
                "published_utc",
                "place",
                "signals",
                "negative_flag",
                "title",
                "text",
                "raw_link",
                "source",
                "lat",
                "lon",
                "id",
            ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for signal in signals:
            for row in signal.iter_output_rows(fieldnames):
                writer.writerow(row)


def write_markdown(path: str, signals: Sequence[NormalisedSignal]) -> None:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    if not signals:
        content = "# Pap Signals\n\n_No signals harvested in this run._\n"
    else:
        header = "| Score | When (UTC) | Zone | Signals | Title |\n"
        separator = "| ---: | :-- | :-- | :-- | :-- |\n"
        rows = []
        for signal in signals:
            score = f"{signal.score:.2f}"
            when = _escape_markdown_cell(signal.timestamp_utc.isoformat())
            zone = _escape_markdown_cell(signal.place or "")
            signals_text = _escape_markdown_cell(", ".join(signal.signals))
            title = _escape_markdown_cell(signal.title)
            link = signal.extra.get("raw_link") if signal.extra else ""
            if link:
                title_cell = f"[{title}]({link})"
            else:
                title_cell = title
            rows.append(f"| {score} | {when} | {zone} | {signals_text} | {title_cell} |")
        content = "# Pap Signals\n\n" + header + separator + "\n".join(rows) + "\n"
    path_obj.write_text(content, encoding="utf-8")


def print_console(signals: Sequence[NormalisedSignal], limit: int = 30) -> None:
    print("\n=== Pap Signals (ranked) ===")
    print(f"{'Score':>5}  {'When (UTC)':<20}  {'Zone':<18}  {'Signals':<28}  Title")
    for signal in signals[:limit]:
        title = signal.title
        if len(title) > 80:
            title = title[:79] + "…"
        signals_text = ", ".join(signal.signals)
        if len(signals_text) > 28:
            signals_text = signals_text[:27] + "…"
        zone = (signal.place or "")[:18]
        print(
            f"{signal.score:>5.2f}  {signal.timestamp_utc.isoformat():<20}  {zone:<18}  {signals_text:<28}  {title}"
        )
