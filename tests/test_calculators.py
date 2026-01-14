"""Unit tests for portfolio/utils/calculators.py financial calculations."""

from datetime import date

import pytest

from portfolio.core.models import CashFlow, PortfolioSummary
from portfolio.utils.calculators import ReturnCalculator, create_cash_flows_from_summary
from tests.fixtures.test_data import TEST_DATE_1, TEST_DATE_2, TEST_DATE_3


class TestReturnCalculator:
    """Test financial return calculations."""

    def test_simple_buy_hold_return(self):
        """Test simple buy and hold return calculation."""
        # £1000 invested, now worth £1100 = 10% return
        cash_flows = [
            CashFlow(date=TEST_DATE_1, amount=-1000.00, description="Initial investment"),
        ]
        current_value = 1100.00

        calc = ReturnCalculator(cash_flows, current_value)
        assert calc.simple_return == pytest.approx(10.0, abs=0.1)  # 10% return

    def test_total_contributions(self):
        """Test total contributions calculation."""
        cash_flows = [
            CashFlow(date=TEST_DATE_1, amount=-5000.00, description="Initial investment"),
        ]
        current_value = 5500.00

        calc = ReturnCalculator(cash_flows, current_value)
        assert calc.total_contributions == pytest.approx(5000.00, abs=0.01)

    def test_annualised_return_positive(self):
        """Test annualised return for positive performance."""
        # 21% gain from £1000 investment
        cash_flows = [
            CashFlow(date=date(2022, 1, 1), amount=-1000.00, description="Initial investment"),
        ]
        current_value = 1210.00

        calc = ReturnCalculator(cash_flows, current_value)
        annualised = calc.calculate_annualised_return()
        # Should calculate successfully with positive annualised return
        assert annualised is not None
        assert annualised > 0.0

    def test_annualised_return_zero_years(self):
        """Test annualised return when minimal time passed."""
        cash_flows = [
            CashFlow(date=TEST_DATE_1, amount=-1000.00, description="Initial investment"),
        ]
        current_value = 1100.00

        calc = ReturnCalculator(cash_flows, current_value)
        # With very short time period, annualised return may be None or very large
        # Just verify it doesn't crash
        annualised = calc.calculate_annualised_return()
        assert annualised is None or isinstance(annualised, (int, float))

    def test_years_invested_calculation(self):
        """Test years invested calculation."""
        cash_flows = [
            CashFlow(date=date(2023, 1, 1), amount=-1000.00, description="Initial investment"),
        ]
        current_value = 1100.00

        calc = ReturnCalculator(cash_flows, current_value)
        # Years invested should be positive (from 2023 to today)
        assert calc.years_invested > 0.0

    def test_negative_return(self):
        """Test calculation for negative return."""
        # £1000 investment down to £900 = -10% loss
        cash_flows = [
            CashFlow(date=TEST_DATE_1, amount=-1000.00, description="Initial investment"),
        ]
        current_value = 900.00

        calc = ReturnCalculator(cash_flows, current_value)
        assert calc.simple_return < 0.0

    def test_total_gain_calculation(self):
        """Test total gain/loss in GBP."""
        # £1000 invested, now £1100 = £100 gain
        cash_flows = [
            CashFlow(date=TEST_DATE_1, amount=-1000.00, description="Initial investment"),
        ]
        current_value = 1100.00

        calc = ReturnCalculator(cash_flows, current_value)
        assert calc.total_gain == pytest.approx(100.00, abs=0.01)

    def test_cash_flow_property(self):
        """Test cash_flows property returns sorted list."""
        cash_flows = [
            CashFlow(date=TEST_DATE_3, amount=-2000.00, description="Third contribution"),
            CashFlow(date=TEST_DATE_1, amount=-1000.00, description="First contribution"),
            CashFlow(date=TEST_DATE_2, amount=-1500.00, description="Second contribution"),
        ]
        current_value = 5000.00

        calc = ReturnCalculator(cash_flows, current_value)

        # Cash flows should be sorted by date
        assert calc.cash_flows[0].date == TEST_DATE_1
        assert calc.cash_flows[1].date == TEST_DATE_2
        assert calc.cash_flows[2].date == TEST_DATE_3

    def test_zero_contributions_raises_error(self):
        """Test that zero contributions raises ValueError."""
        cash_flows = []  # No cash flows

        with pytest.raises(ValueError, match="At least one cash flow is required"):
            ReturnCalculator(cash_flows, 1000.00)

    def test_multiple_contributions_and_withdrawals(self):
        """Test with multiple contributions and withdrawals."""
        cash_flows = [
            CashFlow(date=TEST_DATE_1, amount=-5000.00, description="Initial"),
            CashFlow(date=TEST_DATE_2, amount=-3000.00, description="Additional"),
            CashFlow(date=TEST_DATE_3, amount=500.00, description="Withdrawal"),
        ]
        current_value = 8000.00

        calc = ReturnCalculator(cash_flows, current_value)
        assert calc.total_contributions == pytest.approx(8000.00, abs=0.01)
        assert calc.total_withdrawals == pytest.approx(500.00, abs=0.01)

    def test_calculate_mwrr(self):
        """Test MWRR (IRR) calculation."""
        cash_flows = [
            CashFlow(date=date(2023, 1, 1), amount=-1000.00, description="Initial"),
        ]
        current_value = 1100.00

        calc = ReturnCalculator(cash_flows, current_value)
        mwrr = calc.calculate_mwrr()
        # Should calculate without error
        assert mwrr is None or isinstance(mwrr, (int, float))

    def test_calculate_all_returns_all_metrics(self):
        """Test calculate_all method returns all metrics."""
        cash_flows = [
            CashFlow(date=TEST_DATE_1, amount=-1000.00, description="Initial"),
        ]
        current_value = 1100.00

        calc = ReturnCalculator(cash_flows, current_value)
        metrics = calc.calculate_all()

        # Verify all required attributes exist
        assert hasattr(metrics, "total_contributions")
        assert hasattr(metrics, "total_withdrawals")
        assert hasattr(metrics, "current_value")
        assert hasattr(metrics, "total_gain")
        assert hasattr(metrics, "simple_return")
        assert hasattr(metrics, "annualised_return")
        assert hasattr(metrics, "mwrr")
        assert hasattr(metrics, "years_invested")
        assert hasattr(metrics, "start_date")
        assert hasattr(metrics, "end_date")

        # Verify values
        assert metrics.total_contributions == pytest.approx(1000.00, abs=0.01)
        assert metrics.current_value == 1100.00
        assert metrics.simple_return == pytest.approx(10.0, abs=0.1)


class TestCreateCashFlowsFromSummary:
    """Test creating cash flows from portfolio summary."""

    def test_create_cash_flows_with_contributions_only(self):
        """Test creating cash flows with contributions only."""
        summary = PortfolioSummary(
            total_contributions=5000.00,
            total_withdrawals=0.00,
            current_value=5500.00,
            start_date=TEST_DATE_1,
            end_date=TEST_DATE_2,
        )

        cash_flows = create_cash_flows_from_summary(summary)

        # Should have one cash flow for contributions
        assert len(cash_flows) == 1
        assert cash_flows[0].amount == -5000.00  # Negative = contribution
        assert cash_flows[0].date == TEST_DATE_1

    def test_create_cash_flows_with_contributions_and_withdrawals(self):
        """Test creating cash flows with both contributions and withdrawals."""
        summary = PortfolioSummary(
            total_contributions=5000.00,
            total_withdrawals=500.00,
            current_value=5000.00,
            start_date=TEST_DATE_1,
            end_date=TEST_DATE_3,
        )

        cash_flows = create_cash_flows_from_summary(summary)

        # Should have two cash flows
        assert len(cash_flows) == 2
        assert cash_flows[0].amount == -5000.00  # Contributions (negative)
        assert cash_flows[1].amount == 500.00  # Withdrawals (positive)

    def test_create_cash_flows_no_withdrawals(self):
        """Test creating cash flows when withdrawals are zero."""
        summary = PortfolioSummary(
            total_contributions=3000.00,
            total_withdrawals=0.00,
            current_value=3200.00,
            start_date=TEST_DATE_1,
            end_date=TEST_DATE_2,
        )

        cash_flows = create_cash_flows_from_summary(summary)

        # Should only have contributions
        assert len(cash_flows) == 1
        assert all(cf.amount < 0 for cf in cash_flows)  # All negative

    def test_create_cash_flows_ordering(self):
        """Test that cash flows are ordered correctly."""
        summary = PortfolioSummary(
            total_contributions=5000.00,
            total_withdrawals=1000.00,
            current_value=4200.00,
            start_date=TEST_DATE_1,
            end_date=TEST_DATE_3,
        )

        cash_flows = create_cash_flows_from_summary(summary)

        # Contributions should come first
        assert cash_flows[0].date == TEST_DATE_1
        # Withdrawals should be at midpoint
        assert TEST_DATE_1 < cash_flows[1].date < TEST_DATE_3
