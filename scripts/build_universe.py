from __future__ import annotations

import argparse
from pathlib import Path

from backtests_momentum.config import get_settings
from backtests_momentum.instruments import (
    build_fno_equity_universe,
    build_nse_equity_universe,
    load_instruments,
    write_universe,
)


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(settings.data_dir / "raw" / "instruments" / "nse.json.gz"))
    parser.add_argument("--universe", choices=["fno", "nse"], default="fno")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    records = load_instruments(Path(args.input))
    if args.universe == "fno":
        rows = build_fno_equity_universe(records)
        default_output = settings.data_dir / "processed" / "universe_fno_equities.csv"
    else:
        rows = build_nse_equity_universe(records)
        default_output = settings.data_dir / "processed" / "universe_nse_equities.csv"

    output = Path(args.output) if args.output else default_output
    write_universe(output, rows)
    print(f"Wrote {len(rows)} symbols to {output}")


if __name__ == "__main__":
    main()
