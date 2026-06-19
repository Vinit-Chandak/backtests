from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path


IST = timezone(timedelta(hours=5, minutes=30), name="IST")


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    open_interest: float

    @property
    def day(self) -> date:
        return self.timestamp.date()


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=IST)
    return parsed.astimezone(IST)


def rows_to_candles(rows: list[list[object]]) -> list[Candle]:
    candles: list[Candle] = []
    for row in rows:
        if len(row) < 6:
            continue
        candles.append(
            Candle(
                timestamp=parse_timestamp(str(row[0])),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                open_interest=float(row[6]) if len(row) > 6 and row[6] is not None else 0.0,
            )
        )
    return sorted(candles, key=lambda candle: candle.timestamp)


def write_candles_csv(path: Path, candles: list[Candle]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume", "open_interest"])
        for candle in candles:
            writer.writerow(
                [
                    candle.timestamp.isoformat(),
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                    candle.open_interest,
                ]
            )


def read_candles_csv(path: Path) -> list[Candle]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            Candle(
                timestamp=parse_timestamp(row["timestamp"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                open_interest=float(row.get("open_interest") or 0.0),
            )
            for row in reader
        ]


def group_by_day(candles: list[Candle]) -> dict[date, list[Candle]]:
    grouped: dict[date, list[Candle]] = {}
    for candle in sorted(candles, key=lambda item: item.timestamp):
        grouped.setdefault(candle.day, []).append(candle)
    return grouped


def candle_at_or_before(candles: list[Candle], signal_time: time) -> Candle | None:
    candidates = [candle for candle in candles if candle.timestamp.time() <= signal_time]
    if not candidates:
        return None
    return max(candidates, key=lambda candle: candle.timestamp)


def first_candle(candles: list[Candle]) -> Candle | None:
    return min(candles, key=lambda candle: candle.timestamp) if candles else None


def last_candle(candles: list[Candle]) -> Candle | None:
    return max(candles, key=lambda candle: candle.timestamp) if candles else None
