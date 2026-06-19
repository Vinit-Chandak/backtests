from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from backtests_momentum.candles import write_candles_csv
from backtests_momentum.config import get_settings, require
from backtests_momentum.instruments import read_universe, safe_symbol_filename
from backtests_momentum.upstox import UpstoxClient


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", required=True)
    parser.add_argument("--from-date", required=True, type=parse_date)
    parser.add_argument("--to-date", required=True, type=parse_date)
    parser.add_argument("--unit", choices=["minutes", "hours", "days", "weeks", "months"], default="minutes")
    parser.add_argument("--interval", type=int, default=1)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--limit", type=int, default=0, help="Optional max symbols for a smoke test.")
    parser.add_argument("--skip-existing", action="store_true", help="Resume by skipping non-empty output files.")
    parser.add_argument("--continue-on-error", action="store_true", help="Keep downloading other symbols if one fails.")
    parser.add_argument("--pause-seconds", type=float, default=0.25, help="Delay between API calls.")
    args = parser.parse_args()

    rows = read_universe(Path(args.universe))
    if args.limit:
        rows = rows[: args.limit]

    output_dir = Path(args.output_dir) if args.output_dir else settings.data_dir / "raw" / "candles" / f"{args.unit}_{args.interval}"
    client = UpstoxClient(
        access_token=require(settings.access_token, "UPSTOX_ACCESS_TOKEN"),
        user_agent=settings.user_agent,
        pause_seconds=args.pause_seconds,
    )

    for index, row in enumerate(rows, start=1):
        symbol = row["trading_symbol"]
        instrument_key = row["instrument_key"]
        output = output_dir / safe_symbol_filename(symbol, instrument_key)
        if args.skip_existing and output.exists() and output.stat().st_size > 0:
            print(f"[{index}/{len(rows)}] Skipping {symbol}; already have {output}")
            continue

        print(f"[{index}/{len(rows)}] Fetching {symbol} {instrument_key}")
        try:
            candles = client.historical_candles_chunked(
                instrument_key=instrument_key,
                unit=args.unit,
                interval=args.interval,
                from_date=args.from_date,
                to_date=args.to_date,
            )
        except Exception as exc:
            if not args.continue_on_error:
                raise
            print(f"  ERROR: {symbol} failed: {exc}")
            continue
        write_candles_csv(output, candles)
        print(f"  wrote {len(candles)} candles to {output}")


if __name__ == "__main__":
    main()
