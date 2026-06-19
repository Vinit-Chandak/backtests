from __future__ import annotations

import gzip
import json
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from backtests_momentum.candles import Candle, rows_to_candles


API_BASE = "https://api.upstox.com"
NSE_INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
COMPLETE_INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
DEFAULT_USER_AGENT = "upstox-momentum-backtester/0.1"


def api_headers(user_agent: str = DEFAULT_USER_AGENT, extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": user_agent,
    }
    if extra:
        headers.update(extra)
    return headers


def authorization_url(client_id: str, redirect_uri: str, state: str = "backtest") -> str:
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    return f"{API_BASE}/v2/login/authorization/dialog?{query}"


def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, object]:
    data = urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = Request(
        f"{API_BASE}/v2/login/authorization/token",
        data=data,
        headers=api_headers(user_agent, {"Content-Type": "application/x-www-form-urlencoded"}),
        method="POST",
    )
    return _json_request(request)


def download_instruments(path: Path, source: str = "nse") -> Path:
    url = NSE_INSTRUMENTS_URL if source == "nse" else COMPLETE_INSTRUMENTS_URL
    path.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=60) as response:
        payload = response.read()

    if path.suffix == ".gz":
        path.write_bytes(payload)
    else:
        path.write_text(gzip.decompress(payload).decode("utf-8"), encoding="utf-8")
    return path


class UpstoxClient:
    def __init__(
        self,
        access_token: str,
        pause_seconds: float = 0.25,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.access_token = access_token
        self.pause_seconds = pause_seconds
        self.user_agent = user_agent

    def historical_candles(
        self,
        instrument_key: str,
        unit: str,
        interval: int,
        from_date: date,
        to_date: date,
    ) -> list[Candle]:
        encoded_key = quote(instrument_key, safe="")
        url = f"{API_BASE}/v3/historical-candle/{encoded_key}/{unit}/{interval}/{to_date.isoformat()}/{from_date.isoformat()}"
        request = Request(
            url,
            headers=api_headers(
                self.user_agent,
                {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.access_token}",
                },
            ),
        )
        payload = _json_request(request)
        candles = payload.get("data", {}).get("candles", [])
        if not isinstance(candles, list):
            raise ValueError(f"Unexpected candle response for {instrument_key}")
        time.sleep(self.pause_seconds)
        return rows_to_candles(candles)

    def historical_candles_chunked(
        self,
        instrument_key: str,
        unit: str,
        interval: int,
        from_date: date,
        to_date: date,
    ) -> list[Candle]:
        candles: list[Candle] = []
        for chunk_start, chunk_end in candle_chunks(unit, interval, from_date, to_date):
            candles.extend(self.historical_candles(instrument_key, unit, interval, chunk_start, chunk_end))

        by_timestamp = {candle.timestamp: candle for candle in candles}
        return [by_timestamp[key] for key in sorted(by_timestamp)]


def candle_chunks(unit: str, interval: int, from_date: date, to_date: date) -> list[tuple[date, date]]:
    if from_date > to_date:
        raise ValueError("from_date must be <= to_date")

    if unit == "minutes" and interval <= 15:
        max_days = 30
    elif unit in {"minutes", "hours"}:
        max_days = 90
    elif unit == "days":
        max_days = 3650
    else:
        max_days = 36500

    chunks: list[tuple[date, date]] = []
    cursor = from_date
    while cursor <= to_date:
        end = min(cursor + timedelta(days=max_days - 1), to_date)
        chunks.append((cursor, end))
        cursor = end + timedelta(days=1)
    return chunks


def _json_request(request: Request) -> dict[str, object]:
    try:
        with urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Upstox request failed: HTTP {exc.code}: {body}") from exc
