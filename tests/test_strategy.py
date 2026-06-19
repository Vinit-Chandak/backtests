from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import unittest

from backtests_momentum.candles import Candle
from backtests_momentum.strategy import build_symbol_days, run_gap_backtest, summarize_bucket_results


IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def c(day: int, hh: int, mm: int, open_: float, close: float) -> Candle:
    return Candle(
        timestamp=datetime(2025, 1, day, hh, mm, tzinfo=IST),
        open=open_,
        high=max(open_, close),
        low=min(open_, close),
        close=close,
        volume=1000,
        open_interest=0,
    )


class StrategyTests(unittest.TestCase):
    def test_build_symbol_days_uses_previous_close_signal_and_next_open(self) -> None:
        candles = [
            c(1, 15, 29, 99, 100),
            c(2, 15, 24, 104, 105),
            c(2, 15, 25, 105, 106),
            c(3, 9, 15, 108, 109),
        ]

        rows = build_symbol_days("ABC", candles, time(15, 25))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].symbol, "ABC")
        self.assertEqual(round(rows[0].intraday_change_pct, 2), 6.0)
        self.assertEqual(round(rows[0].next_gap_from_signal_pct, 2), 1.89)

    def test_run_gap_backtest_scores_gainers_and_losers(self) -> None:
        abc = build_symbol_days(
            "ABC",
            [c(1, 15, 29, 99, 100), c(2, 15, 25, 105, 106), c(3, 9, 15, 108, 109)],
            time(15, 25),
        )
        xyz = build_symbol_days(
            "XYZ",
            [c(1, 15, 29, 100, 100), c(2, 15, 25, 95, 94), c(3, 9, 15, 92, 91)],
            time(15, 25),
        )

        results = run_gap_backtest(abc + xyz, [1])

        gainer = next(row for row in results if row.side == "gainer")
        loser = next(row for row in results if row.side == "loser")
        self.assertEqual(gainer.wins, 1)
        self.assertEqual(loser.wins, 1)

        summary = summarize_bucket_results(results)
        gainer_summary = next(row for row in summary if row.side == "gainer")
        loser_summary = next(row for row in summary if row.side == "loser")
        self.assertEqual(gainer_summary.positions, 1)
        self.assertEqual(loser_summary.positions, 1)
        self.assertEqual(gainer_summary.win_rate, 1.0)
        self.assertEqual(gainer_summary.first_day.isoformat(), "2025-01-02")

    def test_run_gap_backtest_filters_by_min_move(self) -> None:
        abc = build_symbol_days(
            "ABC",
            [c(1, 15, 29, 99, 100), c(2, 15, 25, 105, 106), c(3, 9, 15, 108, 109)],
            time(15, 25),
        )
        xyz = build_symbol_days(
            "XYZ",
            [c(1, 15, 29, 100, 100), c(2, 15, 25, 95, 94), c(3, 9, 15, 92, 91)],
            time(15, 25),
        )

        results = run_gap_backtest(abc + xyz, [1], min_move_pct=8.0)

        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
