from __future__ import annotations

import argparse
from datetime import time
from pathlib import Path

from backtests_momentum.config import get_settings
from backtests_momentum.instruments import read_universe
from backtests_momentum.strategy import (
    load_signal_table,
    run_gap_backtest,
    summarize_bucket_results,
    write_bucket_results,
    write_summary_results,
)


def parse_time(value: str) -> time:
    hour, minute = value.split(":", 1)
    return time(int(hour), int(minute))


def parse_top_sizes(value: str) -> list[int]:
    sizes = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not sizes:
        raise argparse.ArgumentTypeError("At least one top size is required.")
    return sizes


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--candles-dir", default=str(settings.data_dir / "raw" / "candles" / "minutes_1"))
    parser.add_argument("--signal-time", type=parse_time, default=time(15, 25))
    parser.add_argument("--top-sizes", type=parse_top_sizes, default=[1, 3, 5])
    parser.add_argument(
        "--min-move-pct",
        type=float,
        default=0.0,
        help="Only rank gainers at or above this move and losers at or below the negative of this move.",
    )
    parser.add_argument("--output", default=str(settings.reports_dir / "momentum_gap.csv"))
    parser.add_argument("--summary-output", default=str(settings.reports_dir / "momentum_gap_summary.csv"))
    parser.add_argument(
        "--universe",
        default=str(settings.data_dir / "processed" / "universe_fno_equities.csv"),
        help="Optional universe CSV used only for coverage warnings.",
    )
    parser.add_argument(
        "--min-symbols",
        type=int,
        default=0,
        help="Fail fast if fewer than this many candle files are available.",
    )
    args = parser.parse_args()

    candles_dir = Path(args.candles_dir)
    candle_files = sorted(candles_dir.glob("*.csv"))
    if not candle_files:
        raise SystemExit(f"No candle CSV files found in {candles_dir}")
    if args.min_symbols and len(candle_files) < args.min_symbols:
        raise SystemExit(
            f"Only found {len(candle_files)} candle files in {candles_dir}; "
            f"--min-symbols requires at least {args.min_symbols}."
        )

    print(f"Found {len(candle_files)} candle files in {candles_dir}")
    universe_path = Path(args.universe) if args.universe else None
    if universe_path and universe_path.exists():
        universe = read_universe(universe_path)
        if len(candle_files) < len(universe):
            print(
                "WARNING: Candle coverage is partial: "
                f"{len(candle_files)} files for {len(universe)} symbols in {universe_path}. "
                "This is probably a smoke-test run."
            )

    records = load_signal_table(candles_dir, args.signal_time)
    results = run_gap_backtest(records, args.top_sizes, min_move_pct=args.min_move_pct)
    summary = summarize_bucket_results(results)
    write_bucket_results(Path(args.output), results)
    write_summary_results(Path(args.summary_output), summary)
    print(f"Built {len(records)} symbol-day records.")
    if args.min_move_pct:
        print(f"Applied min move filter: +/-{args.min_move_pct:.2f}%")
    print(f"Wrote {len(results)} bucket rows to {args.output}")
    print(f"Wrote {len(summary)} summary rows to {args.summary_output}")


if __name__ == "__main__":
    main()
