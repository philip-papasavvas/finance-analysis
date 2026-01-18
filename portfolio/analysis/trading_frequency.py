"""
Trading frequency analysis.

Analyzes how often trades occur across funds, platforms, and tax wrappers.
"""

import logging
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from portfolio.analysis.models import TradingFrequencyMetrics

logger = logging.getLogger(__name__)


class TradingFrequencyAnalyzer:
    """Analyzes trading frequency patterns."""

    def __init__(self, db_path: str | Path = "portfolio.db"):
        """Initialize analyzer with database path."""
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _analyze_by_fund(self) -> list[TradingFrequencyMetrics]:
        """Analyze trading frequency by fund, consolidating by ticker when available."""
        cursor = self.conn.cursor()

        # First, get funds with tickers - consolidate by ticker
        # Use the shortest fund name as the canonical name (usually the cleanest)
        cursor.execute(
            """
            SELECT
                (SELECT t2.fund_name FROM transactions t2
                 JOIN fund_ticker_mapping ftm2 ON t2.fund_name = ftm2.fund_name
                 WHERE ftm2.ticker = ftm.ticker AND t2.excluded = 0
                 ORDER BY LENGTH(t2.fund_name), t2.fund_name LIMIT 1) as fund_name,
                ftm.ticker,
                COUNT(*) as total_trades,
                SUM(CASE WHEN t.transaction_type = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN t.transaction_type = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                MIN(t.date) as first_trade,
                MAX(t.date) as last_trade,
                COUNT(DISTINCT strftime('%Y-%m', t.date)) as active_months
            FROM transactions t
            JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            WHERE t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
            GROUP BY ftm.ticker
            ORDER BY total_trades DESC
        """
        )

        results = []
        for row in cursor.fetchall():
            first_date = datetime.strptime(row["first_trade"], "%Y-%m-%d").date()
            last_date = datetime.strptime(row["last_trade"], "%Y-%m-%d").date()
            months = max(1, row["active_months"])

            results.append(
                TradingFrequencyMetrics(
                    fund_name=row["fund_name"],
                    ticker=row["ticker"],
                    total_trades=row["total_trades"],
                    buy_count=row["buy_count"],
                    sell_count=row["sell_count"],
                    first_trade_date=first_date,
                    last_trade_date=last_date,
                    active_months=months,
                    avg_trades_per_month=row["total_trades"] / months,
                    confidence=1.0,
                )
            )

        # Then get funds without tickers (keep separate by fund_name)
        cursor.execute(
            """
            SELECT
                t.fund_name,
                NULL as ticker,
                COUNT(*) as total_trades,
                SUM(CASE WHEN t.transaction_type = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN t.transaction_type = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                MIN(t.date) as first_trade,
                MAX(t.date) as last_trade,
                COUNT(DISTINCT strftime('%Y-%m', t.date)) as active_months
            FROM transactions t
            LEFT JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            WHERE t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
              AND ftm.ticker IS NULL
            GROUP BY t.fund_name
            ORDER BY total_trades DESC
        """
        )

        for row in cursor.fetchall():
            first_date = datetime.strptime(row["first_trade"], "%Y-%m-%d").date()
            last_date = datetime.strptime(row["last_trade"], "%Y-%m-%d").date()
            months = max(1, row["active_months"])

            results.append(
                TradingFrequencyMetrics(
                    fund_name=row["fund_name"],
                    ticker=row["ticker"],
                    total_trades=row["total_trades"],
                    buy_count=row["buy_count"],
                    sell_count=row["sell_count"],
                    first_trade_date=first_date,
                    last_trade_date=last_date,
                    active_months=months,
                    avg_trades_per_month=row["total_trades"] / months,
                    confidence=1.0,
                )
            )

        # Sort all results by total_trades descending
        results.sort(key=lambda x: x.total_trades, reverse=True)
        return results

    def _analyze_by_platform(self) -> list[TradingFrequencyMetrics]:
        """Analyze trading frequency by platform."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                t.platform,
                COUNT(*) as total_trades,
                SUM(CASE WHEN t.transaction_type = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN t.transaction_type = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                MIN(t.date) as first_trade,
                MAX(t.date) as last_trade,
                COUNT(DISTINCT strftime('%Y-%m', t.date)) as active_months
            FROM transactions t
            WHERE t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
            GROUP BY t.platform
            ORDER BY total_trades DESC
        """
        )

        results = []
        for row in cursor.fetchall():
            first_date = datetime.strptime(row["first_trade"], "%Y-%m-%d").date()
            last_date = datetime.strptime(row["last_trade"], "%Y-%m-%d").date()
            months = max(1, row["active_months"])

            results.append(
                TradingFrequencyMetrics(
                    platform=row["platform"],
                    total_trades=row["total_trades"],
                    buy_count=row["buy_count"],
                    sell_count=row["sell_count"],
                    first_trade_date=first_date,
                    last_trade_date=last_date,
                    active_months=months,
                    avg_trades_per_month=row["total_trades"] / months,
                    confidence=1.0,
                )
            )

        return results

    def _analyze_by_wrapper(self) -> list[TradingFrequencyMetrics]:
        """Analyze trading frequency by tax wrapper."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                t.tax_wrapper,
                COUNT(*) as total_trades,
                SUM(CASE WHEN t.transaction_type = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN t.transaction_type = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                MIN(t.date) as first_trade,
                MAX(t.date) as last_trade,
                COUNT(DISTINCT strftime('%Y-%m', t.date)) as active_months
            FROM transactions t
            WHERE t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
            GROUP BY t.tax_wrapper
            ORDER BY total_trades DESC
        """
        )

        results = []
        for row in cursor.fetchall():
            first_date = datetime.strptime(row["first_trade"], "%Y-%m-%d").date()
            last_date = datetime.strptime(row["last_trade"], "%Y-%m-%d").date()
            months = max(1, row["active_months"])

            results.append(
                TradingFrequencyMetrics(
                    tax_wrapper=row["tax_wrapper"],
                    total_trades=row["total_trades"],
                    buy_count=row["buy_count"],
                    sell_count=row["sell_count"],
                    first_trade_date=first_date,
                    last_trade_date=last_date,
                    active_months=months,
                    avg_trades_per_month=row["total_trades"] / months,
                    confidence=1.0,
                )
            )

        return results

    def _analyze_monthly_pattern(self) -> dict:
        """Analyze monthly trading pattern."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                strftime('%Y-%m', date) as month,
                COUNT(*) as trades,
                SUM(CASE WHEN transaction_type = 'BUY' THEN 1 ELSE 0 END) as buys,
                SUM(CASE WHEN transaction_type = 'SELL' THEN 1 ELSE 0 END) as sells
            FROM transactions
            WHERE excluded = 0
              AND transaction_type IN ('BUY', 'SELL')
            GROUP BY month
            ORDER BY month
        """
        )

        monthly_data = {}
        peak_month = None
        peak_trades = 0

        for row in cursor.fetchall():
            monthly_data[row["month"]] = {
                "trades": row["trades"],
                "buys": row["buys"],
                "sells": row["sells"],
            }
            if row["trades"] > peak_trades:
                peak_trades = row["trades"]
                peak_month = row["month"]

        # Calculate yearly totals
        yearly_totals: dict = defaultdict(lambda: {"trades": 0, "buys": 0, "sells": 0})
        for month, data in monthly_data.items():
            year = month[:4]
            yearly_totals[year]["trades"] += data["trades"]
            yearly_totals[year]["buys"] += data["buys"]
            yearly_totals[year]["sells"] += data["sells"]

        return {
            "monthly": monthly_data,
            "yearly": dict(yearly_totals),
            "peak_month": peak_month,
            "peak_month_trades": peak_trades,
            "total_months": len(monthly_data),
            "avg_trades_per_month": sum(d["trades"] for d in monthly_data.values())
            / len(monthly_data)
            if monthly_data
            else 0,
        }

    def analyze(
        self,
    ) -> tuple[
        list[TradingFrequencyMetrics],
        list[TradingFrequencyMetrics],
        list[TradingFrequencyMetrics],
        dict,
    ]:
        """
        Run full trading frequency analysis.

        Returns:
            Tuple of (by_fund, by_platform, by_wrapper, monthly_pattern)
        """
        logger.info("Starting trading frequency analysis...")

        by_fund = self._analyze_by_fund()
        logger.info(f"  Analyzed {len(by_fund)} unique funds")

        by_platform = self._analyze_by_platform()
        logger.info(f"  Analyzed {len(by_platform)} platforms")

        by_wrapper = self._analyze_by_wrapper()
        logger.info(f"  Analyzed {len(by_wrapper)} tax wrappers")

        monthly = self._analyze_monthly_pattern()
        logger.info(f"  Analyzed {monthly['total_months']} months of trading")

        return by_fund, by_platform, by_wrapper, monthly

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s | %(message)s",
    )

    with TradingFrequencyAnalyzer() as analyzer:
        by_fund, by_platform, by_wrapper, monthly = analyzer.analyze()

        print("\n" + "=" * 60)
        print("TRADING FREQUENCY ANALYSIS")
        print("=" * 60)

        print("\nBy Platform:")
        for m in by_platform:
            print(
                f"  {m.platform:25} | {m.total_trades:>3} trades "
                f"({m.buy_count} buys, {m.sell_count} sells)"
            )

        print("\nBy Tax Wrapper:")
        for m in by_wrapper:
            print(
                f"  {m.tax_wrapper:25} | {m.total_trades:>3} trades "
                f"({m.buy_count} buys, {m.sell_count} sells)"
            )

        print("\nTop 10 Most Traded Funds:")
        for m in by_fund[:10]:
            print(
                f"  {m.fund_name[:40]:40} | {m.total_trades:>3} trades "
                f"| {m.avg_trades_per_month:.2f}/month"
            )

        print("\nMonthly Pattern:")
        print(f"  Peak month: {monthly['peak_month']} ({monthly['peak_month_trades']} trades)")
        print(f"  Average trades/month: {monthly['avg_trades_per_month']:.2f}")

        print("\nYearly Breakdown:")
        for year, data in sorted(monthly["yearly"].items()):
            print(f"  {year}: {data['trades']} trades ({data['buys']} buys, {data['sells']} sells)")
