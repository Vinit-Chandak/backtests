from __future__ import annotations

import argparse
import csv
from pathlib import Path

from backtests_momentum.config import get_settings
from backtests_momentum.instruments import read_universe


def first_and_last_timestamp(path: Path) -> tuple[str, str, int]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        first = ""
        last = ""
        rows = 0
        for row in reader:
            timestamp = row["timestamp"]
            if not first:
                first = timestamp
            last = timestamp
            rows += 1
    return first, last, rows


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--candles-dir", required=True)
    parser.add_argument("--universe", default="")
    args = parser.parse_args()

    candles_dir = Path(args.candles_dir)
    files = sorted(candles_dir.glob("*.csv"))
    if not files:
        raise SystemExit(f"No candle CSV files found in {candles_dir}")

    first_seen = ""
    last_seen = ""
    total_rows = 0
    empty_files = 0
    for path in files:
        first, last, rows = first_and_last_timestamp(path)
        if not rows:
            empty_files += 1
            continue
        total_rows += rows
        first_seen = min(first_seen, first) if first_seen else first
        last_seen = max(last_seen, last) if last_seen else last

    print(f"Candle directory: {candles_dir}")
    print(f"Files: {len(files)}")
    print(f"Empty files: {empty_files}")
    print(f"Rows: {total_rows}")
    print(f"First timestamp: {first_seen or 'n/a'}")
    print(f"Last timestamp: {last_seen or 'n/a'}")

    universe_path = Path(args.universe) if args.universe else settings.data_dir / "processed" / "universe_fno_equities.csv"
    if universe_path.exists():
        universe = read_universe(universe_path)
        print(f"Universe symbols: {len(universe)}")
        if len(files) < len(universe):
            print(f"Missing candle files: {len(universe) - len(files)}")


if __name__ == "__main__":
    main()
