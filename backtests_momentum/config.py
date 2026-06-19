from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_env(path: Path | None = None) -> dict[str, str]:
    env_path = path or PROJECT_ROOT / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        values[key.strip()] = value
        os.environ.setdefault(key.strip(), value)
    return values


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    redirect_uri: str
    access_token: str
    user_agent: str
    data_dir: Path
    reports_dir: Path


def get_settings() -> Settings:
    load_env()
    data_dir = Path(os.environ.get("BACKTEST_DATA_DIR", "data"))
    reports_dir = Path(os.environ.get("BACKTEST_REPORTS_DIR", "reports"))
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    if not reports_dir.is_absolute():
        reports_dir = PROJECT_ROOT / reports_dir

    return Settings(
        client_id=os.environ.get("UPSTOX_CLIENT_ID", ""),
        client_secret=os.environ.get("UPSTOX_CLIENT_SECRET", ""),
        redirect_uri=os.environ.get("UPSTOX_REDIRECT_URI", ""),
        access_token=os.environ.get("UPSTOX_ACCESS_TOKEN", ""),
        user_agent=os.environ.get("UPSTOX_USER_AGENT", "upstox-momentum-backtester/0.1"),
        data_dir=data_dir,
        reports_dir=reports_dir,
    )


def require(value: str, name: str) -> str:
    if not value:
        raise SystemExit(f"Missing {name}. Add it to .env first.")
    return value
