"""
Current holdings analysis with unrealized gains.

Analyzes still-held positions from current_holdings.json,
calculating cost basis from transaction history and unrealized gains.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# LSE stocks: some are quoted in pence, some in GBP
# yfinance returns mixed formats - use heuristic: if price > 500, likely pence
def _convert_lse_price(ticker: str, price: float) -> float:
    """Convert LSE price from pence to GBP if needed."""
    if ticker and ticker.endswith(".L") and price > 500:
        # Likely in pence, convert to GBP
        return price / 100.0
    return price


@dataclass
class HoldingAnalysis:
    """Analysis of a single holding."""

    ticker: str
    fund_name: str
    platform: str
    tax_wrapper: str
    units: float
    current_price: float
    current_value: float
    cost_basis: float
    unrealized_gain: float
    unrealized_gain_pct: float
    price_date: str
    first_buy_date: Optional[str] = None
    total_buys: int = 0
    confidence: float = 1.0
    notes: str = ""
    # Performance metrics
    twr: Optional[float] = None  # Time-weighted return (annualized %)
    mwr: Optional[float] = None  # Money-weighted return (annualized %)
    holding_period_days: int = 0
    # Benchmark comparisons (annualized returns over holding period)
    benchmark_vwrl: Optional[float] = None  # FTSE All-World
    benchmark_vusa: Optional[float] = None  # S&P 500
    benchmark_vfem: Optional[float] = None  # Emerging Markets
    benchmark_vuke: Optional[float] = None  # FTSE 100
    benchmark_ijpn: Optional[float] = None  # Japan

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "fund_name": self.fund_name,
            "platform": self.platform,
            "tax_wrapper": self.tax_wrapper,
            "units": self.units,
            "current_price": self.current_price,
            "current_value": self.current_value,
            "cost_basis": self.cost_basis,
            "unrealized_gain": self.unrealized_gain,
            "unrealized_gain_pct": self.unrealized_gain_pct,
            "price_date": self.price_date,
            "first_buy_date": self.first_buy_date,
            "total_buys": self.total_buys,
            "confidence": self.confidence,
            "notes": self.notes,
            "twr": self.twr,
            "mwr": self.mwr,
            "holding_period_days": self.holding_period_days,
            "benchmark_vwrl": self.benchmark_vwrl,
            "benchmark_vusa": self.benchmark_vusa,
            "benchmark_vfem": self.benchmark_vfem,
            "benchmark_vuke": self.benchmark_vuke,
            "benchmark_ijpn": self.benchmark_ijpn,
        }


class CurrentHoldingsAnalyzer:
    """Analyzes current holdings for unrealized gains."""

    def __init__(
        self,
        db_path: str | Path = "portfolio.db",
        holdings_path: str | Path = "data/current_holdings.json",
    ):
        self.db_path = Path(db_path)
        self.holdings_path = Path(holdings_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def _load_current_holdings(self) -> dict:
        """Load current holdings from JSON file."""
        if not self.holdings_path.exists():
            logger.warning(f"Holdings file not found: {self.holdings_path}")
            return {}

        with open(self.holdings_path) as f:
            return json.load(f)

    def _get_latest_price(self, ticker: str) -> tuple[Optional[float], Optional[str]]:
        """Get latest price for a ticker."""
        cursor = self.conn.cursor()

        # Try direct ticker match
        cursor.execute(
            """
            SELECT close_price, date FROM price_history
            WHERE ticker = ?
            ORDER BY date DESC LIMIT 1
        """,
            (ticker,),
        )
        row = cursor.fetchone()
        if row:
            price = _convert_lse_price(ticker, row["close_price"])
            return price, row["date"]

        # Try with .L suffix for LSE stocks
        if (
            not ticker.endswith(".L")
            and not ticker.startswith("GB")
            and not ticker.startswith("IE")
            and not ticker.startswith("LU")
        ):
            lse_ticker = f"{ticker}.L"
            cursor.execute(
                """
                SELECT close_price, date FROM price_history
                WHERE ticker = ?
                ORDER BY date DESC LIMIT 1
            """,
                (lse_ticker,),
            )
            row = cursor.fetchone()
            if row:
                price = _convert_lse_price(lse_ticker, row["close_price"])
                return price, row["date"]

        return None, None

    def _get_cost_basis(
        self, ticker: str, fund_name: str, platform: str, tax_wrapper: str, units_held: float
    ) -> tuple[float, int, Optional[str], float]:
        """
        Calculate cost basis using FIFO from transaction history.

        Returns:
            (cost_basis, total_buys, first_buy_date, confidence)
        """
        cursor = self.conn.cursor()

        # Map platform names to database values
        platform_map = {
            "Interactive Investor": "INTERACTIVE_INVESTOR",
            "Fidelity": "FIDELITY",
            "InvestEngine": "INVEST_ENGINE",
            "Vanguard": "VANGUARD",
            "Interactive Brokers": "Interactive Brokers",
            "DODL": "DODL",
        }
        db_platform = platform_map.get(platform, platform.upper().replace(" ", "_"))

        # Find transactions that match this holding
        # First try by ticker mapping
        cursor.execute(
            """
            SELECT t.date, t.transaction_type, t.units, t.price_per_unit, t.value
            FROM transactions t
            JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            WHERE ftm.ticker = ?
              AND t.platform = ?
              AND t.tax_wrapper = ?
              AND t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
            ORDER BY t.date
        """,
            (ticker, db_platform, tax_wrapper),
        )
        transactions = cursor.fetchall()

        if not transactions:
            # Try by fund name pattern
            cursor.execute(
                """
                SELECT t.date, t.transaction_type, t.units, t.price_per_unit, t.value
                FROM transactions t
                WHERE t.fund_name LIKE ?
                  AND t.platform = ?
                  AND t.tax_wrapper = ?
                  AND t.excluded = 0
                  AND t.transaction_type IN ('BUY', 'SELL')
                ORDER BY t.date
            """,
                (f"%{fund_name[:20]}%", db_platform, tax_wrapper),
            )
            transactions = cursor.fetchall()

        if not transactions:
            # No matching transactions - return 0 cost basis with low confidence
            return 0.0, 0, None, 0.5

        # FIFO calculation
        lots = []
        total_buys = 0
        first_buy_date = None

        for tx in transactions:
            if tx["transaction_type"] == "BUY":
                lots.append(
                    {
                        "date": tx["date"],
                        "units": tx["units"],
                        "price": tx["price_per_unit"],
                        "remaining": tx["units"],
                    }
                )
                total_buys += 1
                if first_buy_date is None:
                    first_buy_date = tx["date"]
            elif tx["transaction_type"] == "SELL":
                units_to_sell = tx["units"]
                while units_to_sell > 0.001 and lots:
                    lot = lots[0]
                    consumed = min(units_to_sell, lot["remaining"])
                    lot["remaining"] -= consumed
                    units_to_sell -= consumed
                    if lot["remaining"] < 0.001:
                        lots.pop(0)

        # Calculate cost basis from remaining lots
        cost_basis = 0.0
        units_accounted = 0.0
        for lot in lots:
            if lot["remaining"] > 0.001:
                cost_basis += lot["remaining"] * lot["price"]
                units_accounted += lot["remaining"]

        # Check if we have enough lots to cover current holdings
        confidence = 1.0
        if abs(units_accounted - units_held) > units_held * 0.1:
            # More than 10% discrepancy
            confidence = 0.7

        return cost_basis, total_buys, first_buy_date, confidence

    def analyze(self) -> tuple[list[HoldingAnalysis], dict]:
        """
        Analyze all current holdings.

        Returns:
            (list of HoldingAnalysis, summary dict)
        """
        logger.info("Starting current holdings analysis...")

        holdings_data = self._load_current_holdings()
        if not holdings_data:
            logger.warning("No current holdings found")
            return [], {}

        results: list[HoldingAnalysis] = []
        total_value = 0.0
        total_cost = 0.0
        holdings_with_prices = 0
        holdings_without_prices = 0

        for ticker, data in holdings_data.items():
            fund_name = data.get("fund_name", ticker)

            for holding in data.get("holdings", []):
                platform = holding.get("platform", "Unknown")
                tax_wrapper = holding.get("tax_wrapper", "Unknown")
                units = holding.get("units", 0)

                # Get current price
                current_price, price_date = self._get_latest_price(ticker)

                if current_price is None:
                    holdings_without_prices += 1
                    results.append(
                        HoldingAnalysis(
                            ticker=ticker,
                            fund_name=fund_name,
                            platform=platform,
                            tax_wrapper=tax_wrapper,
                            units=units,
                            current_price=0.0,
                            current_value=0.0,
                            cost_basis=0.0,
                            unrealized_gain=0.0,
                            unrealized_gain_pct=0.0,
                            price_date="N/A",
                            confidence=0.3,
                            notes="No price data available",
                        )
                    )
                    continue

                holdings_with_prices += 1
                current_value = units * current_price

                # Get cost basis
                cost_basis, total_buys, first_buy, confidence = self._get_cost_basis(
                    ticker, fund_name, platform, tax_wrapper, units
                )

                unrealized_gain = current_value - cost_basis
                unrealized_gain_pct = (
                    (unrealized_gain / cost_basis * 100) if cost_basis > 0 else 0.0
                )

                notes = ""
                if confidence < 0.9:
                    notes = "Cost basis may be incomplete (pre-history purchases)"

                results.append(
                    HoldingAnalysis(
                        ticker=ticker,
                        fund_name=fund_name,
                        platform=platform,
                        tax_wrapper=tax_wrapper,
                        units=units,
                        current_price=current_price,
                        current_value=current_value,
                        cost_basis=cost_basis,
                        unrealized_gain=unrealized_gain,
                        unrealized_gain_pct=unrealized_gain_pct,
                        price_date=price_date,
                        first_buy_date=first_buy,
                        total_buys=total_buys,
                        confidence=confidence,
                        notes=notes,
                    )
                )

                total_value += current_value
                total_cost += cost_basis

        # Calculate summary
        total_unrealized = total_value - total_cost
        total_unrealized_pct = (total_unrealized / total_cost * 100) if total_cost > 0 else 0.0

        summary = {
            "total_holdings": len(results),
            "holdings_with_prices": holdings_with_prices,
            "holdings_without_prices": holdings_without_prices,
            "total_current_value": total_value,
            "total_cost_basis": total_cost,
            "total_unrealized_gain": total_unrealized,
            "total_unrealized_gain_pct": total_unrealized_pct,
            "by_wrapper": {},
            "by_platform": {},
            "top_gainers": [],
            "top_losers": [],
        }

        # Group by wrapper and platform
        for r in results:
            if r.current_value > 0:
                # By wrapper
                if r.tax_wrapper not in summary["by_wrapper"]:
                    summary["by_wrapper"][r.tax_wrapper] = {"value": 0, "cost": 0, "gain": 0}
                summary["by_wrapper"][r.tax_wrapper]["value"] += r.current_value
                summary["by_wrapper"][r.tax_wrapper]["cost"] += r.cost_basis
                summary["by_wrapper"][r.tax_wrapper]["gain"] += r.unrealized_gain

                # By platform
                if r.platform not in summary["by_platform"]:
                    summary["by_platform"][r.platform] = {"value": 0, "cost": 0, "gain": 0}
                summary["by_platform"][r.platform]["value"] += r.current_value
                summary["by_platform"][r.platform]["cost"] += r.cost_basis
                summary["by_platform"][r.platform]["gain"] += r.unrealized_gain

        # Top gainers and losers (by absolute gain)
        with_cost = [r for r in results if r.cost_basis > 0]
        summary["top_gainers"] = sorted(with_cost, key=lambda x: x.unrealized_gain, reverse=True)[
            :5
        ]
        summary["top_losers"] = sorted(with_cost, key=lambda x: x.unrealized_gain)[:5]

        logger.info(f"  Analyzed {len(results)} holdings")
        logger.info(f"  With prices: {holdings_with_prices}, Without: {holdings_without_prices}")
        logger.info(f"  Total value: £{total_value:,.2f}")
        logger.info(f"  Unrealized gain: £{total_unrealized:,.2f} ({total_unrealized_pct:+.2f}%)")

        return results, summary

    def close(self) -> None:
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

    with CurrentHoldingsAnalyzer() as analyzer:
        results, summary = analyzer.analyze()

        print("\n" + "=" * 60)
        print("CURRENT HOLDINGS ANALYSIS")
        print("=" * 60)
        print(f"Total holdings: {summary['total_holdings']}")
        print(f"With price data: {summary['holdings_with_prices']}")
        print(f"Without price data: {summary['holdings_without_prices']}")
        print()
        print(f"Total Current Value: £{summary['total_current_value']:,.2f}")
        print(f"Total Cost Basis: £{summary['total_cost_basis']:,.2f}")
        print(
            f"Unrealized Gain/Loss: £{summary['total_unrealized_gain']:,.2f} ({summary['total_unrealized_gain_pct']:+.2f}%)"
        )
        print()

        print("By Tax Wrapper:")
        for wrapper, data in summary["by_wrapper"].items():
            gain_pct = (data["gain"] / data["cost"] * 100) if data["cost"] > 0 else 0
            print(
                f"  {wrapper}: £{data['value']:,.2f} (gain: £{data['gain']:,.2f}, {gain_pct:+.2f}%)"
            )

        print()
        print("Top 5 Gainers:")
        for r in summary["top_gainers"]:
            print(
                f"  {r.fund_name[:35]:35} | {r.tax_wrapper:4} | "
                f"£{r.unrealized_gain:>10,.2f} ({r.unrealized_gain_pct:+.1f}%)"
            )

        print()
        print("Top 5 Losers:")
        for r in summary["top_losers"]:
            print(
                f"  {r.fund_name[:35]:35} | {r.tax_wrapper:4} | "
                f"£{r.unrealized_gain:>10,.2f} ({r.unrealized_gain_pct:+.1f}%)"
            )
