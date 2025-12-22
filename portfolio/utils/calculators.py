"""
Return calculators for portfolio analyzer.

Calculates various return metrics including simple return, MWRR (IRR),
and annualised returns.
"""
import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional

from scipy.optimize import brentq

from portfolio.core.models import CashFlow, PortfolioSummary
from portfolio.utils.helpers import calculate_years_between


logger = logging.getLogger(__name__)


@dataclass
class ReturnMetrics:
    """Container for calculated return metrics."""
    total_contributions: float
    total_withdrawals: float
    current_value: float
    total_gain: float
    simple_return: float  # Percentage
    annualised_return: Optional[float]  # Percentage, may be None if calculation fails
    mwrr: Optional[float]  # Money-weighted rate of return (IRR), percentage
    years_invested: float
    start_date: date
    end_date: date

    def __str__(self) -> str:
        """Format return metrics as a readable string."""
        lines = [
            f"Return Metrics ({self.start_date} to {self.end_date})",
            f"  Total Contributions: £{self.total_contributions:,.2f}",
            f"  Total Withdrawals:   £{self.total_withdrawals:,.2f}",
            f"  Current Value:       £{self.current_value:,.2f}",
            f"  Total Gain:          £{self.total_gain:,.2f}",
            f"  Simple Return:       {self.simple_return:+.2f}%",
        ]

        if self.annualised_return is not None:
            lines.append(f"  Annualised Return:   {self.annualised_return:+.2f}%")

        if self.mwrr is not None:
            lines.append(f"  MWRR (IRR):          {self.mwrr:+.2f}%")

        lines.append(f"  Years Invested:      {self.years_invested:.2f}")

        return "\n".join(lines)


class ReturnCalculator:
    """
    Calculate investment returns from cash flows.

    Supports simple return, annualised return, and MWRR (IRR) calculations.
    """

    def __init__(self, cash_flows: list[CashFlow], current_value: float):
        """
        Initialise the calculator.

        Args:
            cash_flows: List of CashFlow objects (negative = money in, positive = money out).
            current_value: Current portfolio value.
        """
        self.cash_flows = sorted(cash_flows, key=lambda cf: cf.date)
        self.current_value = current_value

        if not self.cash_flows:
            raise ValueError("At least one cash flow is required")

        logger.info(
            f"ReturnCalculator initialised with {len(cash_flows)} cash flows, "
            f"current value: £{current_value:,.2f}"
        )

    @property
    def start_date(self) -> date:
        """First cash flow date."""
        return self.cash_flows[0].date

    @property
    def end_date(self) -> date:
        """Current date (today or last cash flow date)."""
        return date.today()

    @property
    def total_contributions(self) -> float:
        """Sum of all contributions (money in)."""
        return sum(abs(cf.amount) for cf in self.cash_flows if cf.is_inflow)

    @property
    def total_withdrawals(self) -> float:
        """Sum of all withdrawals (money out)."""
        return sum(cf.amount for cf in self.cash_flows if cf.is_outflow)

    @property
    def total_gain(self) -> float:
        """Total gain/loss."""
        return self.current_value + self.total_withdrawals - self.total_contributions

    @property
    def simple_return(self) -> float:
        """Simple return as a percentage."""
        if self.total_contributions == 0:
            return 0.0
        return (self.total_gain / self.total_contributions) * 100

    @property
    def years_invested(self) -> float:
        """Number of years between first cash flow and today."""
        return calculate_years_between(self.start_date, self.end_date)

    def calculate_annualised_return(self) -> Optional[float]:
        """
        Calculate annualised return using compound growth formula.

        Returns:
            Annualised return as a percentage, or None if calculation fails.
        """
        if self.total_contributions == 0 or self.years_invested <= 0:
            return None

        # Simple annualised return: (1 + total_return)^(1/years) - 1
        total_return = self.simple_return / 100

        if total_return <= -1:
            # Can't annualise a total loss of 100% or more
            return None

        try:
            annualised = ((1 + total_return) ** (1 / self.years_invested) - 1) * 100
            return annualised
        except (ValueError, ZeroDivisionError) as e:
            logger.warning(f"Could not calculate annualised return: {e}")
            return None

    def calculate_mwrr(self, end_date: Optional[date] = None) -> Optional[float]:
        """
        Calculate Money-Weighted Rate of Return (MWRR/IRR).

        Uses the internal rate of return method, accounting for
        the timing and size of all cash flows.

        Args:
            end_date: End date for calculation. Defaults to today.

        Returns:
            MWRR as a percentage, or None if calculation fails.
        """
        if end_date is None:
            end_date = date.today()

        # Build list of all cash flows including final value
        all_flows = [(cf.date, cf.amount) for cf in self.cash_flows]
        all_flows.append((end_date, self.current_value))  # Final value is positive

        # Sort by date
        all_flows.sort(key=lambda x: x[0])

        first_date = all_flows[0][0]

        def years_from_start(d: date) -> float:
            return (d - first_date).days / 365.25

        def npv(rate: float) -> float:
            """Calculate NPV at a given rate."""
            if rate <= -1:
                return float("inf")

            total = 0.0
            for flow_date, amount in all_flows:
                t = years_from_start(flow_date)
                total += amount / ((1 + rate) ** t)
            return total

        try:
            # Find the rate that makes NPV = 0
            irr = brentq(npv, -0.99, 10.0, maxiter=1000)
            mwrr = irr * 100
            logger.debug(f"Calculated MWRR: {mwrr:.2f}%")
            return mwrr
        except (ValueError, RuntimeError) as e:
            logger.warning(f"Could not calculate MWRR: {e}")
            return None

    def calculate_all(self, end_date: Optional[date] = None) -> ReturnMetrics:
        """
        Calculate all return metrics.

        Args:
            end_date: End date for calculations. Defaults to today.

        Returns:
            ReturnMetrics object with all calculated values.
        """
        if end_date is None:
            end_date = date.today()

        return ReturnMetrics(
            total_contributions=self.total_contributions,
            total_withdrawals=self.total_withdrawals,
            current_value=self.current_value,
            total_gain=self.total_gain,
            simple_return=self.simple_return,
            annualised_return=self.calculate_annualised_return(),
            mwrr=self.calculate_mwrr(end_date),
            years_invested=self.years_invested,
            start_date=self.start_date,
            end_date=end_date,
        )


def create_cash_flows_from_summary(summary: PortfolioSummary) -> list[CashFlow]:
    """
    Create simplified cash flows from a portfolio summary.

    This is a convenience function for when detailed cash flow
    data is not available.

    Args:
        summary: PortfolioSummary with contribution/withdrawal totals.

    Returns:
        List of CashFlow objects.
    """
    cash_flows = []

    # Single contribution at start date
    if summary.total_contributions > 0:
        cash_flows.append(
            CashFlow(
                date=summary.start_date,
                amount=-summary.total_contributions,
                description="Total contributions",
            )
        )

    # Single withdrawal at midpoint (if any)
    if summary.total_withdrawals > 0:
        midpoint = date.fromordinal(
            (summary.start_date.toordinal() + summary.end_date.toordinal()) // 2
        )
        cash_flows.append(
            CashFlow(
                date=midpoint,
                amount=summary.total_withdrawals,
                description="Total withdrawals",
            )
        )

    return cash_flows


if __name__ == "__main__":
    # Example usage
    import logging
    from datetime import date

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # Example: ISA cash flows
    cash_flows = [
        CashFlow(date(2022, 8, 1), 3000.00, "Withdrawal"),
        CashFlow(date(2023, 4, 1), -5000.00, "Annual subscription"),
        CashFlow(date(2024, 4, 1), -5000.00, "Annual subscription"),
    ]

    current_value = 8000.00

    # Calculate returns
    calculator = ReturnCalculator(cash_flows, current_value)
    metrics = calculator.calculate_all(end_date=date(2025, 4, 1))

    print("\nExample ISA Return Metrics:")
    print("=" * 50)
    print(metrics)
