from __future__ import annotations

import argparse
from pathlib import Path

from backtests_momentum.config import get_settings
from backtests_momentum.upstox import download_instruments


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["nse", "complete"], default="nse")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    settings = get_settings()
    output = Path(args.output) if args.output else settings.data_dir / "raw" / "instruments" / f"{args.source}.json.gz"
    if not output.is_absolute():
        output = settings.data_dir.parent / output
    path = download_instruments(output, args.source)
    print(f"Downloaded instruments to {path}")


if __name__ == "__main__":
    main()
