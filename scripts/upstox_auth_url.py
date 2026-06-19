from __future__ import annotations

from backtests_momentum.config import get_settings, require
from backtests_momentum.upstox import authorization_url


def main() -> None:
    settings = get_settings()
    client_id = require(settings.client_id, "UPSTOX_CLIENT_ID")
    redirect_uri = require(settings.redirect_uri, "UPSTOX_REDIRECT_URI")
    print(authorization_url(client_id, redirect_uri))


if __name__ == "__main__":
    main()
