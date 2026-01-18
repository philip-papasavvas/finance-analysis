"""
Holding period analysis using FIFO lot matching.

Calculates how long positions were held before being sold,
categorizing by holding period thresholds.
"""

import logging
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from portfolio.analysis.models import (
    HoldingPeriodCategory,
    HoldingPeriodResult,
    Lot,
)

logger = logging.getLogger(__name__)


@dataclass
class FundKey:
    """Key for grouping transactions by fund/platform/wrapper."""

    fund_name: str
    platform: str
    tax_wrapper: str

    def __hash__(self):
        return hash((self.fund_name, self.platform, self.tax_wrapper))

    def __eq__(self, other):
        if not isinstance(other, FundKey):
            return False
        return (
            self.fund_name == other.fund_name
            and self.platform == other.platform
            and self.tax_wrapper == other.tax_wrapper
        )


class HoldingPeriodAnalyzer:
    """Analyzes holding periods using FIFO lot matching."""

    def __init__(self, db_path: str | Path = "portfolio.db"):
        """Initialize analyzer with database path."""
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _get_transactions_for_analysis(self) -> list[dict]:
        """Get all BUY/SELL transactions sorted by date."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                t.id,
                t.fund_name,
                t.platform,
                t.tax_wrapper,
                t.date,
                t.transaction_type,
                t.units,
                t.price_per_unit,
                t.value,
                ftm.ticker
            FROM transactions t
            LEFT JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            WHERE t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
            ORDER BY t.date, t.id
        """
        )
        return [dict(row) for row in cursor.fetchall()]

    def _group_transactions_by_fund(self, transactions: list[dict]) -> dict[FundKey, list[dict]]:
        """Group transactions by fund/platform/wrapper combination."""
        grouped: dict[FundKey, list[dict]] = defaultdict(list)
        for tx in transactions:
            key = FundKey(
                fund_name=tx["fund_name"],
                platform=tx["platform"],
                tax_wrapper=tx["tax_wrapper"],
            )
            grouped[key].append(tx)
        return grouped

    def _process_fund_transactions(
        self,
        fund_key: FundKey,
        transactions: list[dict],
    ) -> tuple[list[HoldingPeriodResult], list[str]]:
        """
        Process transactions for a single fund using FIFO.

        Returns:
            Tuple of (holding period results, data quality issues)
        """
        results: list[HoldingPeriodResult] = []
        issues: list[str] = []
        lot_queue: list[Lot] = []

        # Get ticker from first transaction (if available)
        ticker = transactions[0].get("ticker") if transactions else None

        for tx in transactions:
            tx_date = datetime.strptime(tx["date"], "%Y-%m-%d").date()

            if tx["transaction_type"] == "BUY":
                # Add to lot queue
                lot = Lot(
                    buy_date=tx_date,
                    units=tx["units"],
                    price_per_unit=tx["price_per_unit"],
                    remaining_units=tx["units"],
                    fund_name=tx["fund_name"],
                    platform=tx["platform"],
                    tax_wrapper=tx["tax_wrapper"],
                    transaction_id=tx["id"],
                )
                lot_queue.append(lot)

            elif tx["transaction_type"] == "SELL":
                units_to_sell = tx["units"]
                sell_price = tx["price_per_unit"]
                sell_date = tx_date

                # Consume lots FIFO until sell is fulfilled
                while units_to_sell > 0.001 and lot_queue:
                    lot = lot_queue[0]

                    if lot.is_exhausted:
                        lot_queue.pop(0)
                        continue

                    consumed = lot.consume(units_to_sell)
                    units_to_sell -= consumed

                    # Calculate holding period result
                    holding_days = (sell_date - lot.buy_date).days
                    buy_value = consumed * lot.price_per_unit
                    sell_value = consumed * sell_price
                    gain_loss = sell_value - buy_value
                    gain_loss_pct = (gain_loss / buy_value * 100) if buy_value > 0 else 0.0

                    result = HoldingPeriodResult(
                        fund_name=fund_key.fund_name,
                        ticker=ticker,
                        platform=fund_key.platform,
                        tax_wrapper=fund_key.tax_wrapper,
                        buy_date=lot.buy_date,
                        sell_date=sell_date,
                        holding_days=holding_days,
                        units_sold=consumed,
                        buy_price=lot.price_per_unit,
                        sell_price=sell_price,
                        buy_value=buy_value,
                        sell_value=sell_value,
                        gain_loss=gain_loss,
                        gain_loss_pct=gain_loss_pct,
                        category=HoldingPeriodCategory.from_days(holding_days),
                        confidence=1.0,
                    )
                    results.append(result)

                    # Remove exhausted lot
                    if lot.is_exhausted:
                        lot_queue.pop(0)

                # Check if sell couldn't be fully matched
                if units_to_sell > 0.001:
                    issues.append(
                        f"{fund_key.fund_name} ({fund_key.platform}/{fund_key.tax_wrapper}): "
                        f"SELL on {sell_date} has {units_to_sell:.4f} units with no matching BUY lots"
                    )
                    # Still record a result but with lower confidence
                    if results and results[-1].sell_date == sell_date:
                        results[-1] = HoldingPeriodResult(
                            fund_name=results[-1].fund_name,
                            ticker=results[-1].ticker,
                            platform=results[-1].platform,
                            tax_wrapper=results[-1].tax_wrapper,
                            buy_date=results[-1].buy_date,
                            sell_date=results[-1].sell_date,
                            holding_days=results[-1].holding_days,
                            units_sold=results[-1].units_sold,
                            buy_price=results[-1].buy_price,
                            sell_price=results[-1].sell_price,
                            buy_value=results[-1].buy_value,
                            sell_value=results[-1].sell_value,
                            gain_loss=results[-1].gain_loss,
                            gain_loss_pct=results[-1].gain_loss_pct,
                            category=results[-1].category,
                            confidence=0.7,  # Lower confidence due to unmatched units
                        )

        return results, issues

    def analyze(self) -> tuple[list[HoldingPeriodResult], dict, list[str]]:
        """
        Run full holding period analysis.

        Returns:
            Tuple of (results, summary_dict, data_quality_issues)
        """
        logger.info("Starting holding period analysis (FIFO method)...")

        transactions = self._get_transactions_for_analysis()
        logger.info(f"  Loaded {len(transactions)} BUY/SELL transactions")

        grouped = self._group_transactions_by_fund(transactions)
        logger.info(f"  Grouped into {len(grouped)} fund/platform/wrapper combinations")

        all_results: list[HoldingPeriodResult] = []
        all_issues: list[str] = []

        for fund_key, fund_txs in grouped.items():
            results, issues = self._process_fund_transactions(fund_key, fund_txs)
            all_results.extend(results)
            all_issues.extend(issues)

        # Calculate summary
        summary = self._calculate_summary(all_results)

        logger.info(f"  Analyzed {len(all_results)} holding period records")
        if all_issues:
            logger.warning(f"  Found {len(all_issues)} data quality issues")

        return all_results, summary, all_issues

    def _calculate_summary(self, results: list[HoldingPeriodResult]) -> dict:
        """Calculate summary statistics for holding period results."""
        if not results:
            return {
                "total_holdings_analyzed": 0,
                "by_category": {},
                "avg_holding_days": 0,
                "avg_gain_loss_pct": 0,
                "quick_flips_count": 0,
                "quick_flips_pct": 0,
            }

        # Group by category
        by_category: dict[HoldingPeriodCategory, list[HoldingPeriodResult]] = defaultdict(list)
        for result in results:
            by_category[result.category].append(result)

        # Calculate category summaries
        category_summary = {}
        for category in HoldingPeriodCategory:
            cat_results = by_category.get(category, [])
            if cat_results:
                category_summary[category.value] = {
                    "count": len(cat_results),
                    "pct_of_total": len(cat_results) / len(results) * 100,
                    "avg_gain_loss_pct": sum(r.gain_loss_pct for r in cat_results)
                    / len(cat_results),
                    "total_gain_loss": sum(r.gain_loss for r in cat_results),
                    "label": category.label,
                    "flag": category.flag,
                }
            else:
                category_summary[category.value] = {
                    "count": 0,
                    "pct_of_total": 0,
                    "avg_gain_loss_pct": 0,
                    "total_gain_loss": 0,
                    "label": category.label,
                    "flag": category.flag,
                }

        quick_flips = [r for r in results if r.is_quick_flip]

        return {
            "total_holdings_analyzed": len(results),
            "by_category": category_summary,
            "avg_holding_days": sum(r.holding_days for r in results) / len(results),
            "avg_gain_loss_pct": sum(r.gain_loss_pct for r in results) / len(results),
            "quick_flips_count": len(quick_flips),
            "quick_flips_pct": len(quick_flips) / len(results) * 100 if results else 0,
            "total_gain_loss": sum(r.gain_loss for r in results),
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

    with HoldingPeriodAnalyzer() as analyzer:
        results, summary, issues = analyzer.analyze()

        print("\n" + "=" * 60)
        print("HOLDING PERIOD SUMMARY")
        print("=" * 60)
        print(f"Total holdings analyzed: {summary['total_holdings_analyzed']}")
        print(f"Average holding period: {summary['avg_holding_days']:.1f} days")
        print(f"Average gain/loss: {summary['avg_gain_loss_pct']:+.2f}%")
        print(
            f"Quick flips (<30 days): {summary['quick_flips_count']} ({summary['quick_flips_pct']:.1f}%)"
        )
        print()

        print("By Category:")
        for cat, stats in summary["by_category"].items():
            if stats["count"] > 0:
                print(
                    f"  {stats['label']:>15}: {stats['count']:>3} holdings "
                    f"({stats['pct_of_total']:>5.1f}%) | "
                    f"Avg: {stats['avg_gain_loss_pct']:>+7.2f}% | "
                    f"{stats['flag']}"
                )

        if issues:
            print()
            print("Data Quality Issues:")
            for issue in issues[:10]:
                print(f"  - {issue}")
            if len(issues) > 10:
                print(f"  ... and {len(issues) - 10} more")
