from __future__ import annotations

import argparse

from backtests_momentum.config import get_settings, require
from backtests_momentum.upstox import exchange_code_for_token


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--code", required=True, help="Single-use code from the Upstox redirect URL.")
    args = parser.parse_args()

    settings = get_settings()
    payload = exchange_code_for_token(
        code=args.code,
        client_id=require(settings.client_id, "UPSTOX_CLIENT_ID"),
        client_secret=require(settings.client_secret, "UPSTOX_CLIENT_SECRET"),
        redirect_uri=require(settings.redirect_uri, "UPSTOX_REDIRECT_URI"),
        user_agent=settings.user_agent,
    )
    access_token = payload.get("access_token")
    if not access_token:
        print(payload)
        raise SystemExit("Token response did not include access_token.")
    print(access_token)


if __name__ == "__main__":
    main()
