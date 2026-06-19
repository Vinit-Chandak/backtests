from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path

from backtests_momentum.candles import Candle, candle_at_or_before, first_candle, group_by_day, last_candle, read_candles_csv


@dataclass(frozen=True)
class SymbolDay:
    symbol: str
    day: date
    previous_close: float
    signal_price: float
    next_open: float
    intraday_change_pct: float
    next_gap_from_signal_pct: float
    next_gap_from_prev_close_pct: float


@dataclass(frozen=True)
class BucketResult:
    day: date
    side: str
    top_n: int
    symbols: str
    wins: int
    count: int
    win_rate: float
    average_gap_from_signal_pct: float
    average_gap_from_prev_close_pct: float


@dataclass(frozen=True)
class SummaryResult:
    side: str
    top_n: int
    first_day: date
    last_day: date
    days: int
    positions: int
    wins: int
    win_rate: float
    average_gap_from_signal_pct: float
    average_gap_from_prev_close_pct: float


def symbol_from_candle_file(path: Path) -> str:
    return path.name.split("__", 1)[0]


def build_symbol_days(symbol: str, candles: list[Candle], signal_time: time) -> list[SymbolDay]:
    by_day = group_by_day(candles)
    days = sorted(by_day)
    records: list[SymbolDay] = []

    for index in range(1, len(days) - 1):
        previous_day = days[index - 1]
        current_day = days[index]
        next_day = days[index + 1]

        previous_close_candle = last_candle(by_day[previous_day])
        signal_candle = candle_at_or_before(by_day[current_day], signal_time)
        next_open_candle = first_candle(by_day[next_day])
        if not previous_close_candle or not signal_candle or not next_open_candle:
            continue
        if previous_close_candle.close <= 0 or signal_candle.close <= 0:
            continue

        records.append(
            SymbolDay(
                symbol=symbol,
                day=current_day,
                previous_close=previous_close_candle.close,
                signal_price=signal_candle.close,
                next_open=next_open_candle.open,
                intraday_change_pct=(signal_candle.close / previous_close_candle.close - 1.0) * 100.0,
                next_gap_from_signal_pct=(next_open_candle.open / signal_candle.close - 1.0) * 100.0,
                next_gap_from_prev_close_pct=(next_open_candle.open / previous_close_candle.close - 1.0) * 100.0,
            )
        )

    return records


def load_signal_table(candles_dir: Path, signal_time: time) -> list[SymbolDay]:
    records: list[SymbolDay] = []
    for path in sorted(candles_dir.glob("*.csv")):
        symbol = symbol_from_candle_file(path)
        candles = read_candles_csv(path)
        records.extend(build_symbol_days(symbol, candles, signal_time))
    return records


def run_gap_backtest(
    records: list[SymbolDay],
    top_sizes: list[int],
    min_move_pct: float = 0.0,
) -> list[BucketResult]:
    by_day: dict[date, list[SymbolDay]] = {}
    for record in records:
        by_day.setdefault(record.day, []).append(record)

    results: list[BucketResult] = []
    for day, day_records in sorted(by_day.items()):
        ranked = sorted(day_records, key=lambda row: row.intraday_change_pct, reverse=True)
        for top_n in top_sizes:
            gainers = [row for row in ranked if row.intraday_change_pct >= min_move_pct][:top_n]
            losers = [row for row in reversed(ranked) if row.intraday_change_pct <= -min_move_pct][:top_n]
            if len(gainers) == top_n:
                results.append(_bucket_result(day, "gainer", top_n, gainers))
            if len(losers) == top_n:
                results.append(_bucket_result(day, "loser", top_n, losers))
    return results


def _bucket_result(day: date, side: str, top_n: int, rows: list[SymbolDay]) -> BucketResult:
    if side == "gainer":
        wins = sum(1 for row in rows if row.next_gap_from_signal_pct > 0)
    else:
        wins = sum(1 for row in rows if row.next_gap_from_signal_pct < 0)

    return BucketResult(
        day=day,
        side=side,
        top_n=top_n,
        symbols=",".join(row.symbol for row in rows),
        wins=wins,
        count=len(rows),
        win_rate=wins / len(rows) if rows else 0.0,
        average_gap_from_signal_pct=sum(row.next_gap_from_signal_pct for row in rows) / len(rows),
        average_gap_from_prev_close_pct=sum(row.next_gap_from_prev_close_pct for row in rows) / len(rows),
    )


def write_bucket_results(path: Path, rows: list[BucketResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "day",
                "side",
                "top_n",
                "symbols",
                "wins",
                "count",
                "win_rate",
                "average_gap_from_signal_pct",
                "average_gap_from_prev_close_pct",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "day": row.day.isoformat(),
                    "side": row.side,
                    "top_n": row.top_n,
                    "symbols": row.symbols,
                    "wins": row.wins,
                    "count": row.count,
                    "win_rate": f"{row.win_rate:.4f}",
                    "average_gap_from_signal_pct": f"{row.average_gap_from_signal_pct:.4f}",
                    "average_gap_from_prev_close_pct": f"{row.average_gap_from_prev_close_pct:.4f}",
                }
            )


def summarize_bucket_results(rows: list[BucketResult]) -> list[SummaryResult]:
    grouped: dict[tuple[str, int], list[BucketResult]] = {}
    for row in rows:
        grouped.setdefault((row.side, row.top_n), []).append(row)

    summary: list[SummaryResult] = []
    for (side, top_n), bucket_rows in sorted(grouped.items()):
        positions = sum(row.count for row in bucket_rows)
        wins = sum(row.wins for row in bucket_rows)
        days = sorted(row.day for row in bucket_rows)
        summary.append(
            SummaryResult(
                side=side,
                top_n=top_n,
                first_day=days[0],
                last_day=days[-1],
                days=len(bucket_rows),
                positions=positions,
                wins=wins,
                win_rate=wins / positions if positions else 0.0,
                average_gap_from_signal_pct=sum(
                    row.average_gap_from_signal_pct * row.count for row in bucket_rows
                )
                / positions
                if positions
                else 0.0,
                average_gap_from_prev_close_pct=sum(
                    row.average_gap_from_prev_close_pct * row.count for row in bucket_rows
                )
                / positions
                if positions
                else 0.0,
            )
        )
    return summary


def write_summary_results(path: Path, rows: list[SummaryResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "side",
                "top_n",
                "first_day",
                "last_day",
                "days",
                "positions",
                "wins",
                "win_rate",
                "average_gap_from_signal_pct",
                "average_gap_from_prev_close_pct",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "side": row.side,
                    "top_n": row.top_n,
                    "first_day": row.first_day.isoformat(),
                    "last_day": row.last_day.isoformat(),
                    "days": row.days,
                    "positions": row.positions,
                    "wins": row.wins,
                    "win_rate": f"{row.win_rate:.4f}",
                    "average_gap_from_signal_pct": f"{row.average_gap_from_signal_pct:.4f}",
                    "average_gap_from_prev_close_pct": f"{row.average_gap_from_prev_close_pct:.4f}",
                }
            )
