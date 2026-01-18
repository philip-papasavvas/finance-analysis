"""
Performance analysis: Time-Weighted Return (TWR) and Money-Weighted Return (MWR).

TWR: Measures compound growth rate, removing impact of cash flows.
MWR: Internal rate of return accounting for timing of investments.

Includes benchmark comparisons against:
- VWRL.L: Vanguard FTSE All-World ETF
- VUSA.L: Vanguard S&P 500 ETF
- VFEM.L: Vanguard FTSE Emerging Markets ETF
"""

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

from scipy.optimize import brentq

logger = logging.getLogger(__name__)

# Benchmark tickers for comparison
BENCHMARKS = {
    "VWRL.L": "FTSE All-World",
    "VUSA.L": "S&P 500",
    "VFEM.L": "Emerging Markets",
    "VUKE.L": "FTSE 100",
    "IJPN.L": "Japan",
}


@dataclass
class BenchmarkReturn:
    """Return for a benchmark over a specific period."""

    ticker: str
    name: str
    return_pct: Optional[float]  # Annualized return %
    start_date: str
    end_date: str
    start_price: Optional[float]
    end_price: Optional[float]


@dataclass
class HoldingPerformance:
    """Performance metrics for a single holding."""

    ticker: str
    fund_name: str
    platform: str
    tax_wrapper: str
    current_units: float
    current_value: float
    total_invested: float
    total_withdrawn: float
    twr: Optional[float]  # Time-weighted return (annualized %)
    mwr: Optional[float]  # Money-weighted return (annualized %)
    holding_period_days: int
    first_transaction: str
    last_transaction: str
    num_transactions: int
    # Benchmark comparisons (vs TWR since it's comparable)
    benchmarks: dict[str, BenchmarkReturn] = field(default_factory=dict)

    def alpha_vs(self, benchmark_ticker: str) -> Optional[float]:
        """Calculate alpha (excess return) vs a benchmark."""
        if self.twr is None:
            return None
        bench = self.benchmarks.get(benchmark_ticker)
        if bench is None or bench.return_pct is None:
            return None
        return self.twr - bench.return_pct


@dataclass
class WrapperPerformance:
    """Aggregate performance by tax wrapper."""

    wrapper: str
    current_value: float
    total_invested: float
    total_withdrawn: float
    twr: Optional[float]
    mwr: Optional[float]
    num_holdings: int
    # Benchmark comparisons for the wrapper
    benchmarks: dict[str, BenchmarkReturn] = field(default_factory=dict)


class PerformanceAnalyzer:
    """Analyzes TWR and MWR for portfolio holdings."""

    def __init__(
        self,
        db_path: str | Path = "portfolio.db",
        holdings_path: str | Path = "data/current_holdings.json",
    ):
        self.db_path = Path(db_path)
        self.holdings_path = Path(holdings_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def _load_current_holdings(self) -> dict:
        """Load current holdings from JSON."""
        if not self.holdings_path.exists():
            return {}
        with open(self.holdings_path) as f:
            return json.load(f)

    def _get_price_series(self, ticker: str) -> dict[str, float]:
        """Get price history for a ticker as {date: price} dict."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT date, close_price FROM price_history
            WHERE ticker = ?
            ORDER BY date
            """,
            (ticker,),
        )
        prices = {}
        for row in cursor.fetchall():
            price = row["close_price"]
            # Handle LSE pence conversion
            if ticker.endswith(".L") and price > 500:
                price = price / 100.0
            prices[row["date"]] = price
        return prices

    def _calculate_benchmark_return(
        self, benchmark_ticker: str, start_date: str, end_date: str
    ) -> BenchmarkReturn:
        """
        Calculate benchmark return over a specific period.

        Args:
            benchmark_ticker: Ticker symbol (e.g., VWRL.L)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            BenchmarkReturn with annualized return
        """
        prices = self._get_price_series(benchmark_ticker)
        benchmark_name = BENCHMARKS.get(benchmark_ticker, benchmark_ticker)

        if not prices:
            return BenchmarkReturn(
                ticker=benchmark_ticker,
                name=benchmark_name,
                return_pct=None,
                start_date=start_date,
                end_date=end_date,
                start_price=None,
                end_price=None,
            )

        # Find closest prices to start and end dates
        sorted_dates = sorted(prices.keys())

        # Find start price (first available on or after start_date)
        start_price = None
        actual_start = None
        for d in sorted_dates:
            if d >= start_date:
                start_price = prices[d]
                actual_start = d
                break

        # Find end price (last available on or before end_date)
        end_price = None
        actual_end = None
        for d in reversed(sorted_dates):
            if d <= end_date:
                end_price = prices[d]
                actual_end = d
                break

        if start_price is None or end_price is None or actual_start is None or actual_end is None:
            return BenchmarkReturn(
                ticker=benchmark_ticker,
                name=benchmark_name,
                return_pct=None,
                start_date=start_date,
                end_date=end_date,
                start_price=start_price,
                end_price=end_price,
            )

        # Calculate total return
        total_return = (end_price / start_price) - 1

        # Annualize
        try:
            start_dt = datetime.strptime(actual_start, "%Y-%m-%d")
            end_dt = datetime.strptime(actual_end, "%Y-%m-%d")
            days = (end_dt - start_dt).days
            if days > 0:
                years = days / 365.25
                annualized = (1 + total_return) ** (1 / years) - 1
                return BenchmarkReturn(
                    ticker=benchmark_ticker,
                    name=benchmark_name,
                    return_pct=annualized * 100,
                    start_date=actual_start,
                    end_date=actual_end,
                    start_price=start_price,
                    end_price=end_price,
                )
        except Exception as e:
            logger.warning(f"Error calculating benchmark return for {benchmark_ticker}: {e}")

        return BenchmarkReturn(
            ticker=benchmark_ticker,
            name=benchmark_name,
            return_pct=total_return * 100 if total_return else None,
            start_date=start_date,
            end_date=end_date,
            start_price=start_price,
            end_price=end_price,
        )

    def _get_benchmarks_for_period(
        self, start_date: str, end_date: str
    ) -> dict[str, BenchmarkReturn]:
        """Get all benchmark returns for a specific period."""
        benchmarks = {}
        for ticker in BENCHMARKS.keys():
            benchmarks[ticker] = self._calculate_benchmark_return(ticker, start_date, end_date)
        return benchmarks

    def _get_transactions(self, ticker: str, platform: str, tax_wrapper: str) -> list[dict]:
        """Get transactions for a holding."""
        cursor = self.conn.cursor()

        # Map platform names
        platform_map = {
            "Interactive Investor": "INTERACTIVE_INVESTOR",
            "Fidelity": "FIDELITY",
            "InvestEngine": "INVEST_ENGINE",
            "Vanguard": "VANGUARD",
            "Interactive Brokers": "Interactive Brokers",
        }
        db_platform = platform_map.get(platform, platform)

        # Try ticker mapping first
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
        rows = cursor.fetchall()

        if not rows:
            # Try direct fund name match
            cursor.execute(
                """
                SELECT t.date, t.transaction_type, t.units, t.price_per_unit, t.value
                FROM transactions t
                WHERE t.platform = ?
                  AND t.tax_wrapper = ?
                  AND t.excluded = 0
                  AND t.transaction_type IN ('BUY', 'SELL')
                  AND EXISTS (
                      SELECT 1 FROM fund_ticker_mapping ftm
                      WHERE ftm.fund_name = t.fund_name AND ftm.ticker = ?
                  )
                ORDER BY t.date
                """,
                (db_platform, tax_wrapper, ticker),
            )
            rows = cursor.fetchall()

        return [dict(row) for row in rows]

    def _calculate_twr(
        self, transactions: list[dict], prices: dict[str, float], current_value: float
    ) -> Optional[float]:
        """
        Calculate Time-Weighted Return.

        TWR = (1 + r1) * (1 + r2) * ... * (1 + rn) - 1
        Where ri is the return for each sub-period between cash flows.
        """
        if not transactions or not prices:
            return None

        # Sort transactions by date
        txns = sorted(transactions, key=lambda x: x["date"])

        # Get first and last dates
        first_date = txns[0]["date"]
        sorted_prices = sorted(prices.keys())
        if not sorted_prices:
            return None

        last_price_date = sorted_prices[-1]

        # Build sub-periods
        sub_period_returns = []
        units_held = 0.0
        prev_value = 0.0

        for txn in txns:
            txn_date = txn["date"]

            # Get price on transaction date (or closest before)
            price_on_date = None
            for d in sorted(prices.keys(), reverse=True):
                if d <= txn_date:
                    price_on_date = prices[d]
                    break

            if price_on_date is None:
                continue

            # Calculate value before transaction
            value_before = units_held * price_on_date

            # Calculate sub-period return if we had holdings
            if prev_value > 0 and value_before > 0:
                period_return = (value_before / prev_value) - 1
                sub_period_returns.append(1 + period_return)

            # Apply transaction
            if txn["transaction_type"] == "BUY":
                units_held += txn["units"]
            else:  # SELL
                units_held -= txn["units"]

            # Value after transaction
            prev_value = units_held * price_on_date

        # Final sub-period to current value
        if prev_value > 0 and current_value > 0:
            final_return = (current_value / prev_value) - 1
            sub_period_returns.append(1 + final_return)

        if not sub_period_returns:
            return None

        # Calculate TWR
        twr = 1.0
        for r in sub_period_returns:
            twr *= r
        twr -= 1

        # Annualize
        try:
            first_dt = datetime.strptime(first_date, "%Y-%m-%d")
            last_dt = datetime.strptime(last_price_date, "%Y-%m-%d")
            days = (last_dt - first_dt).days
            if days > 0:
                years = days / 365.25
                annualized = (1 + twr) ** (1 / years) - 1
                return annualized * 100
        except (ValueError, TypeError):
            pass

        return twr * 100

    def _calculate_mwr(
        self, transactions: list[dict], current_value: float, current_date: str
    ) -> Optional[float]:
        """
        Calculate Money-Weighted Return (IRR).

        Finds the rate r such that:
        Sum of PV(cash flows) + PV(current value) = 0
        """
        if not transactions:
            return None

        # Build cash flow series: negative for buys, positive for sells
        cash_flows = []
        dates = []

        for txn in transactions:
            txn_date = datetime.strptime(txn["date"], "%Y-%m-%d")
            if txn["transaction_type"] == "BUY":
                cf = -abs(txn["value"])  # Outflow
            else:
                cf = abs(txn["value"])  # Inflow
            cash_flows.append(cf)
            dates.append(txn_date)

        # Add current value as final inflow
        try:
            end_date = datetime.strptime(current_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            end_date = datetime.now()

        cash_flows.append(current_value)
        dates.append(end_date)

        if len(cash_flows) < 2:
            return None

        # Calculate days from first date
        first_date = min(dates)
        days_from_start = [(d - first_date).days for d in dates]
        years_from_start = [d / 365.25 for d in days_from_start]

        # NPV function
        def npv(rate):
            if rate <= -1:
                return float("inf")
            total = 0.0
            for cf, years in zip(cash_flows, years_from_start):
                total += cf / ((1 + rate) ** years)
            return total

        # Find IRR using Brent's method
        try:
            irr = brentq(npv, -0.99, 10.0, maxiter=1000)
            return irr * 100  # Return as percentage
        except (ValueError, RuntimeError):
            # Try Newton-Raphson if Brent fails
            try:
                from scipy.optimize import newton

                irr = newton(npv, 0.1, maxiter=1000)
                return irr * 100
            except (ValueError, RuntimeError):
                return None

    def analyze(self) -> tuple[list[HoldingPerformance], dict]:
        """Analyze TWR and MWR for all current holdings."""
        holdings_data = self._load_current_holdings()
        results = []

        # Get latest price date
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(date) as max_date FROM price_history")
        row = cursor.fetchone()
        current_date = row["max_date"] if row else datetime.now().strftime("%Y-%m-%d")

        for ticker, data in holdings_data.items():
            fund_name = data.get("fund_name", ticker)
            prices = self._get_price_series(ticker)

            for holding in data.get("holdings", []):
                platform = holding.get("platform", "Unknown")
                wrapper = holding.get("tax_wrapper", "Unknown")
                units = holding.get("units", 0)

                # Get current price
                if prices:
                    current_price = list(prices.values())[-1]
                else:
                    current_price = 0
                current_value = units * current_price

                # Get transactions
                transactions = self._get_transactions(ticker, platform, wrapper)

                if not transactions:
                    logger.warning(f"No transactions found for {ticker} at {platform}/{wrapper}")
                    continue

                # Calculate metrics
                total_invested = sum(
                    t["value"] for t in transactions if t["transaction_type"] == "BUY"
                )
                total_withdrawn = sum(
                    t["value"] for t in transactions if t["transaction_type"] == "SELL"
                )

                first_txn = min(t["date"] for t in transactions)
                last_txn = max(t["date"] for t in transactions)

                try:
                    first_dt = datetime.strptime(first_txn, "%Y-%m-%d")
                    current_dt = datetime.strptime(current_date, "%Y-%m-%d")
                    holding_days = (current_dt - first_dt).days
                except (ValueError, TypeError):
                    holding_days = 0

                # Calculate returns
                twr = self._calculate_twr(transactions, prices, current_value)
                mwr = self._calculate_mwr(transactions, current_value, current_date)

                # Calculate benchmark returns for the same period
                benchmarks = self._get_benchmarks_for_period(first_txn, current_date)

                results.append(
                    HoldingPerformance(
                        ticker=ticker,
                        fund_name=fund_name,
                        platform=platform,
                        tax_wrapper=wrapper,
                        current_units=units,
                        current_value=current_value,
                        total_invested=total_invested,
                        total_withdrawn=total_withdrawn,
                        twr=twr,
                        mwr=mwr,
                        holding_period_days=holding_days,
                        first_transaction=first_txn,
                        last_transaction=last_txn,
                        num_transactions=len(transactions),
                        benchmarks=benchmarks,
                    )
                )

        # Aggregate by wrapper
        wrapper_summary = {}
        for wrapper in ["ISA", "GIA", "SIPP"]:
            wrapper_holdings = [r for r in results if r.tax_wrapper == wrapper]
            if wrapper_holdings:
                total_value = sum(h.current_value for h in wrapper_holdings)
                total_invested = sum(h.total_invested for h in wrapper_holdings)
                total_withdrawn = sum(h.total_withdrawn for h in wrapper_holdings)

                # Weighted average TWR/MWR
                valid_twr = [
                    (h.twr, h.current_value) for h in wrapper_holdings if h.twr is not None
                ]
                valid_mwr = [
                    (h.mwr, h.current_value) for h in wrapper_holdings if h.mwr is not None
                ]

                avg_twr = None
                if valid_twr:
                    total_weight = sum(w for _, w in valid_twr)
                    if total_weight > 0:
                        avg_twr = sum(t * w for t, w in valid_twr) / total_weight

                avg_mwr = None
                if valid_mwr:
                    total_weight = sum(w for _, w in valid_mwr)
                    if total_weight > 0:
                        avg_mwr = sum(m * w for m, w in valid_mwr) / total_weight

                # Calculate weighted average start date for benchmark comparison
                # Weight by current value (larger positions have more influence on period)
                weighted_dates = []
                for h in wrapper_holdings:
                    if h.first_transaction and h.current_value > 0:
                        try:
                            dt = datetime.strptime(h.first_transaction, "%Y-%m-%d")
                            weighted_dates.append((dt, h.current_value))
                        except (ValueError, TypeError):
                            pass

                wrapper_benchmarks = {}
                if weighted_dates:
                    total_weight = sum(w for _, w in weighted_dates)
                    if total_weight > 0:
                        # Weighted average date as ordinal
                        avg_ordinal = (
                            sum(dt.toordinal() * w for dt, w in weighted_dates) / total_weight
                        )
                        avg_start_date = datetime.fromordinal(int(avg_ordinal)).strftime("%Y-%m-%d")
                        wrapper_benchmarks = self._get_benchmarks_for_period(
                            avg_start_date, current_date
                        )

                wrapper_summary[wrapper] = WrapperPerformance(
                    wrapper=wrapper,
                    current_value=total_value,
                    total_invested=total_invested,
                    total_withdrawn=total_withdrawn,
                    twr=avg_twr,
                    mwr=avg_mwr,
                    num_holdings=len(wrapper_holdings),
                    benchmarks=wrapper_benchmarks,
                )

        return results, wrapper_summary
