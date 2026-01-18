"""
Price impact analysis.

Compares transaction execution prices to market close prices
to assess trading quality.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from portfolio.analysis.models import (
    PriceImpactClassification,
    PriceImpactResult,
)

logger = logging.getLogger(__name__)

# Tolerance for "neutral" classification (within 0.5% of market)
NEUTRAL_TOLERANCE_PCT = 0.5

# LSE stocks are quoted in pence, but transactions store in pounds
# Tickers ending in .L need conversion (divide market price by 100)
LSE_PENCE_SUFFIX = ".L"


def _normalize_market_price(ticker: str, market_price: float, execution_price: float) -> float:
    """
    Normalize market price to match transaction price units.

    LSE stocks (.L suffix) are quoted in pence but transactions are in GBP.
    Detect this by checking if market_price is approximately 100x execution_price.
    """
    if ticker and ticker.endswith(LSE_PENCE_SUFFIX):
        # Check if there's a ~100x difference (indicating pence vs pounds)
        ratio = market_price / execution_price if execution_price > 0 else 0
        if 80 < ratio < 120:  # Roughly 100x difference with some tolerance
            return market_price / 100.0  # Convert pence to pounds
    return market_price


class PriceImpactAnalyzer:
    """Analyzes price impact of trades vs market prices."""

    def __init__(self, db_path: str | Path = "portfolio.db"):
        """Initialize analyzer with database path."""
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _get_transactions_with_prices(self) -> list[dict]:
        """Get transactions joined with market prices."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                t.id,
                t.date,
                t.fund_name,
                ftm.ticker,
                t.transaction_type,
                t.price_per_unit as execution_price,
                ph.close_price as market_price,
                t.units,
                t.value
            FROM transactions t
            INNER JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            INNER JOIN price_history ph ON ftm.ticker = ph.ticker AND t.date = ph.date
            WHERE t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
              AND t.price_per_unit > 0
              AND ph.close_price > 0
            ORDER BY t.date
        """
        )
        return [dict(row) for row in cursor.fetchall()]

    def _get_transactions_missing_prices(self) -> int:
        """Count transactions without matching price data."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as count
            FROM transactions t
            INNER JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            LEFT JOIN price_history ph ON ftm.ticker = ph.ticker AND t.date = ph.date
            WHERE t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
              AND ph.id IS NULL
        """
        )
        return cursor.fetchone()["count"]

    def _classify_impact(
        self,
        transaction_type: str,
        execution_price: float,
        market_price: float,
    ) -> PriceImpactClassification:
        """
        Classify the price impact as favorable, neutral, or unfavorable.

        For BUY: favorable = bought below market
        For SELL: favorable = sold above market
        """
        diff_pct = ((execution_price - market_price) / market_price) * 100

        # Within tolerance = neutral
        if abs(diff_pct) <= NEUTRAL_TOLERANCE_PCT:
            return PriceImpactClassification.NEUTRAL

        if transaction_type == "BUY":
            # Buying below market is favorable
            if execution_price < market_price:
                return PriceImpactClassification.FAVORABLE
            else:
                return PriceImpactClassification.UNFAVORABLE
        else:  # SELL
            # Selling above market is favorable
            if execution_price > market_price:
                return PriceImpactClassification.FAVORABLE
            else:
                return PriceImpactClassification.UNFAVORABLE

    def analyze(self) -> tuple[list[PriceImpactResult], dict, int]:
        """
        Run full price impact analysis.

        Returns:
            Tuple of (results, summary_dict, transactions_missing_prices)
        """
        logger.info("Starting price impact analysis...")

        transactions = self._get_transactions_with_prices()
        missing_count = self._get_transactions_missing_prices()

        logger.info(f"  Found {len(transactions)} transactions with matching price data")
        logger.info(f"  Missing price data for {missing_count} transactions")

        results: list[PriceImpactResult] = []

        for tx in transactions:
            tx_date = datetime.strptime(tx["date"], "%Y-%m-%d").date()
            execution_price = tx["execution_price"]
            raw_market_price = tx["market_price"]
            ticker = tx["ticker"]

            # Normalize market price (handle LSE pence vs GBP)
            market_price = _normalize_market_price(ticker, raw_market_price, execution_price)

            price_diff = execution_price - market_price
            price_diff_pct = (price_diff / market_price) * 100 if market_price > 0 else 0
            value_impact = price_diff * tx["units"]

            classification = self._classify_impact(
                tx["transaction_type"],
                execution_price,
                market_price,
            )

            result = PriceImpactResult(
                date=tx_date,
                fund_name=tx["fund_name"],
                ticker=tx["ticker"],
                transaction_type=tx["transaction_type"],
                execution_price=execution_price,
                market_price=market_price,
                price_difference=price_diff,
                price_difference_pct=price_diff_pct,
                value_impact=value_impact,
                units=tx["units"],
                classification=classification,
                confidence=0.85,  # Lower confidence due to intraday vs close comparison
            )
            results.append(result)

        summary = self._calculate_summary(results, len(transactions), missing_count)

        return results, summary, missing_count

    def _calculate_summary(
        self,
        results: list[PriceImpactResult],
        total_with_prices: int,
        missing_count: int,
    ) -> dict:
        """Calculate summary statistics for price impact."""
        if not results:
            return {
                "total_analyzed": 0,
                "missing_prices": missing_count,
                "favorable_count": 0,
                "unfavorable_count": 0,
                "neutral_count": 0,
                "favorable_pct": 0,
                "avg_deviation_pct": 0,
                "total_favorable_impact": 0,
                "total_unfavorable_impact": 0,
                "net_impact": 0,
            }

        favorable = [r for r in results if r.classification == PriceImpactClassification.FAVORABLE]
        unfavorable = [
            r for r in results if r.classification == PriceImpactClassification.UNFAVORABLE
        ]
        neutral = [r for r in results if r.classification == PriceImpactClassification.NEUTRAL]

        favorable_impact = sum(abs(r.value_impact) for r in favorable)
        unfavorable_impact = sum(abs(r.value_impact) for r in unfavorable)

        # For favorable trades, the impact is positive (saved money on buys, got more on sells)
        # For unfavorable, it's negative
        net_impact = sum(
            -r.value_impact if r.transaction_type == "BUY" else r.value_impact for r in results
        )

        return {
            "total_analyzed": len(results),
            "missing_prices": missing_count,
            "favorable_count": len(favorable),
            "unfavorable_count": len(unfavorable),
            "neutral_count": len(neutral),
            "favorable_pct": len(favorable) / len(results) * 100 if results else 0,
            "unfavorable_pct": len(unfavorable) / len(results) * 100 if results else 0,
            "neutral_pct": len(neutral) / len(results) * 100 if results else 0,
            "avg_deviation_pct": sum(abs(r.price_difference_pct) for r in results) / len(results),
            "total_favorable_impact": favorable_impact,
            "total_unfavorable_impact": unfavorable_impact,
            "net_impact": net_impact,
            "by_type": {
                "BUY": {
                    "count": len([r for r in results if r.transaction_type == "BUY"]),
                    "favorable": len(
                        [
                            r
                            for r in results
                            if r.transaction_type == "BUY"
                            and r.classification == PriceImpactClassification.FAVORABLE
                        ]
                    ),
                    "unfavorable": len(
                        [
                            r
                            for r in results
                            if r.transaction_type == "BUY"
                            and r.classification == PriceImpactClassification.UNFAVORABLE
                        ]
                    ),
                },
                "SELL": {
                    "count": len([r for r in results if r.transaction_type == "SELL"]),
                    "favorable": len(
                        [
                            r
                            for r in results
                            if r.transaction_type == "SELL"
                            and r.classification == PriceImpactClassification.FAVORABLE
                        ]
                    ),
                    "unfavorable": len(
                        [
                            r
                            for r in results
                            if r.transaction_type == "SELL"
                            and r.classification == PriceImpactClassification.UNFAVORABLE
                        ]
                    ),
                },
            },
        }

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

    with PriceImpactAnalyzer() as analyzer:
        results, summary, missing = analyzer.analyze()

        print("\n" + "=" * 60)
        print("PRICE IMPACT ANALYSIS")
        print("=" * 60)
        print(f"Transactions analyzed: {summary['total_analyzed']}")
        print(f"Missing price data: {summary['missing_prices']}")
        print()
        print(
            f"Favorable trades:   {summary['favorable_count']:>3} ({summary['favorable_pct']:.1f}%)"
        )
        print(
            f"Unfavorable trades: {summary['unfavorable_count']:>3} ({summary['unfavorable_pct']:.1f}%)"
        )
        print(f"Neutral trades:     {summary['neutral_count']:>3} ({summary['neutral_pct']:.1f}%)")
        print()
        print(f"Average deviation from market: {summary['avg_deviation_pct']:.2f}%")
        print(f"Net impact: £{summary['net_impact']:,.2f}")

        if results:
            # Top favorable
            favorable = sorted(
                [r for r in results if r.is_favorable],
                key=lambda x: abs(x.value_impact),
                reverse=True,
            )
            if favorable:
                print("\nTop 5 Favorable Trades:")
                for r in favorable[:5]:
                    print(
                        f"  {r.date} {r.transaction_type:4} {r.fund_name[:30]:30} | "
                        f"{r.price_difference_pct:+.2f}% | £{abs(r.value_impact):,.2f}"
                    )

            # Top unfavorable
            unfavorable = sorted(
                [r for r in results if r.classification == PriceImpactClassification.UNFAVORABLE],
                key=lambda x: abs(x.value_impact),
                reverse=True,
            )
            if unfavorable:
                print("\nTop 5 Unfavorable Trades:")
                for r in unfavorable[:5]:
                    print(
                        f"  {r.date} {r.transaction_type:4} {r.fund_name[:30]:30} | "
                        f"{r.price_difference_pct:+.2f}% | £{abs(r.value_impact):,.2f}"
                    )
