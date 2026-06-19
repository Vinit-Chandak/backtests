from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path


def load_instruments(path: Path) -> list[dict[str, object]]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))

    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                return value
        raise ValueError(f"Could not find instrument list in {path}")
    if not isinstance(payload, list):
        raise ValueError(f"Expected instrument list in {path}")
    return payload


def build_fno_equity_universe(records: list[dict[str, object]]) -> list[dict[str, str]]:
    equities: dict[str, dict[str, object]] = {
        str(row.get("instrument_key")): row
        for row in records
        if row.get("segment") == "NSE_EQ" and row.get("instrument_type") == "EQ"
    }

    fno_underlying_keys = {
        str(row.get("underlying_key"))
        for row in records
        if row.get("segment") == "NSE_FO"
        and row.get("instrument_type") in {"FUT", "CE", "PE"}
        and row.get("underlying_type") == "EQUITY"
        and row.get("underlying_key")
    }

    universe: list[dict[str, str]] = []
    for key in sorted(fno_underlying_keys):
        equity = equities.get(key)
        if not equity:
            continue
        universe.append(
            {
                "trading_symbol": str(equity.get("trading_symbol", "")),
                "instrument_key": str(equity.get("instrument_key", "")),
                "name": str(equity.get("name", "")),
                "isin": str(equity.get("isin", "")),
            }
        )
    return sorted(universe, key=lambda item: item["trading_symbol"])


def build_nse_equity_universe(records: list[dict[str, object]]) -> list[dict[str, str]]:
    universe = [
        {
            "trading_symbol": str(row.get("trading_symbol", "")),
            "instrument_key": str(row.get("instrument_key", "")),
            "name": str(row.get("name", "")),
            "isin": str(row.get("isin", "")),
        }
        for row in records
        if row.get("segment") == "NSE_EQ" and row.get("instrument_type") == "EQ"
    ]
    return sorted(universe, key=lambda item: item["trading_symbol"])


def write_universe(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["trading_symbol", "instrument_key", "name", "isin"])
        writer.writeheader()
        writer.writerows(rows)


def read_universe(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def safe_symbol_filename(symbol: str, instrument_key: str) -> str:
    cleaned_symbol = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in symbol)
    cleaned_key = "".join(ch if ch.isalnum() else "_" for ch in instrument_key)
    return f"{cleaned_symbol}__{cleaned_key}.csv"
