"""Unit tests for portfolio/core/models.py data models."""

from datetime import date

import pytest

from portfolio.core.models import (
    Holding,
    PortfolioSummary,
    Transaction,
    TransactionType,
)
from tests.fixtures.test_data import (
    TEST_DATE_1,
    TEST_DATE_2,
    TEST_AMOUNT_1,
    TEST_UNITS_1,
    TEST_PRICE_1,
    TEST_FUND_NAME_1,
    TEST_PLATFORM_FIDELITY,
    TEST_WRAPPER_ISA,
)


class TestTransaction:
    """Test Transaction model."""

    def test_transaction_creation(self):
        """Test creating a transaction."""
        tx = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=float(TEST_UNITS_1),
            price_per_unit=float(TEST_PRICE_1),
            value=float(TEST_AMOUNT_1),
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
        )

        assert tx.date == TEST_DATE_1
        assert tx.fund_name == TEST_FUND_NAME_1
        assert tx.transaction_type == TransactionType.BUY
        assert tx.units == float(TEST_UNITS_1)
        assert tx.price_per_unit == float(TEST_PRICE_1)
        assert tx.value == float(TEST_AMOUNT_1)
        assert tx.platform == TEST_PLATFORM_FIDELITY
        assert tx.tax_wrapper == TEST_WRAPPER_ISA

    def test_transaction_is_buy(self):
        """Test Transaction.is_buy property."""
        tx_buy = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=100.0,
            price_per_unit=10.0,
            value=1000.0,
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
        )
        assert tx_buy.is_buy is True

        tx_sell = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.SELL,
            units=100.0,
            price_per_unit=10.0,
            value=1000.0,
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
        )
        assert tx_sell.is_buy is False

    def test_transaction_is_sell(self):
        """Test Transaction.is_sell property."""
        tx_sell = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.SELL,
            units=100.0,
            price_per_unit=10.0,
            value=1000.0,
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
        )
        assert tx_sell.is_sell is True

        tx_buy = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=100.0,
            price_per_unit=10.0,
            value=1000.0,
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
        )
        assert tx_buy.is_sell is False

    def test_transaction_to_dict(self):
        """Test Transaction.to_dict() serialization."""
        tx = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=100.0,
            price_per_unit=10.0,
            value=1000.0,
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
        )

        tx_dict = tx.to_dict()

        assert isinstance(tx_dict, dict)
        assert tx_dict["Fund Name"] == TEST_FUND_NAME_1
        assert tx_dict["Units"] == 100.0
        assert tx_dict["Price (£)"] == 10.0
        assert tx_dict["Value (£)"] == 1000.0
        assert "Buy/Sell" in tx_dict
        assert "Tax Wrapper" in tx_dict
        assert "Platform" in tx_dict
        assert "Date" in tx_dict

    def test_transaction_optional_fields(self):
        """Test Transaction with optional fields."""
        tx = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=100.0,
            price_per_unit=10.0,
            value=1000.0,
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
            currency="USD",
            sedol="1234567",
            reference="REF-001",
            raw_description="Sample description",
        )

        assert tx.currency == "USD"
        assert tx.sedol == "1234567"
        assert tx.reference == "REF-001"
        assert tx.raw_description == "Sample description"


class TestHolding:
    """Test Holding model."""

    def test_holding_creation(self):
        """Test creating a holding."""
        holding = Holding(
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
            fund_name=TEST_FUND_NAME_1,
            units=100.0,
            current_price=12.0,
            current_value=1200.0,
            book_cost=1000.0,
        )

        assert holding.platform == TEST_PLATFORM_FIDELITY
        assert holding.tax_wrapper == TEST_WRAPPER_ISA
        assert holding.fund_name == TEST_FUND_NAME_1
        assert holding.units == 100.0
        assert holding.current_price == 12.0
        assert holding.current_value == 1200.0
        assert holding.book_cost == 1000.0

    def test_holding_gain(self):
        """Test Holding.gain property."""
        holding = Holding(
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
            fund_name=TEST_FUND_NAME_1,
            units=100.0,
            current_price=12.0,
            current_value=1200.0,
            book_cost=1000.0,
        )

        assert holding.gain == 200.0  # 1200 - 1000

    def test_holding_gain_negative(self):
        """Test Holding.gain property with loss."""
        holding = Holding(
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
            fund_name=TEST_FUND_NAME_1,
            units=100.0,
            current_price=8.0,
            current_value=800.0,
            book_cost=1000.0,
        )

        assert holding.gain == -200.0  # 800 - 1000

    def test_holding_gain_percentage(self):
        """Test Holding.gain_percentage property."""
        holding = Holding(
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
            fund_name=TEST_FUND_NAME_1,
            units=100.0,
            current_price=12.0,
            current_value=1200.0,
            book_cost=1000.0,
        )

        assert holding.gain_percentage == 20.0  # (200 / 1000) * 100

    def test_holding_gain_percentage_zero_book_cost(self):
        """Test Holding.gain_percentage with zero book cost."""
        holding = Holding(
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
            fund_name=TEST_FUND_NAME_1,
            units=100.0,
            current_price=12.0,
            current_value=1200.0,
            book_cost=0.0,
        )

        assert holding.gain_percentage == 0.0


class TestPortfolioSummary:
    """Test PortfolioSummary model."""

    def test_portfolio_summary_creation(self):
        """Test creating a portfolio summary."""
        summary = PortfolioSummary(
            total_contributions=5000.0,
            total_withdrawals=1000.0,
            current_value=5500.0,
            start_date=TEST_DATE_1,
            end_date=TEST_DATE_2,
        )

        assert summary.total_contributions == 5000.0
        assert summary.total_withdrawals == 1000.0
        assert summary.current_value == 5500.0
        assert summary.start_date == TEST_DATE_1
        assert summary.end_date == TEST_DATE_2

    def test_portfolio_summary_net_contributions(self):
        """Test PortfolioSummary.net_contributions property."""
        summary = PortfolioSummary(
            total_contributions=5000.0,
            total_withdrawals=1000.0,
            current_value=5500.0,
            start_date=TEST_DATE_1,
            end_date=TEST_DATE_2,
        )

        assert summary.net_contributions == 4000.0  # 5000 - 1000

    def test_portfolio_summary_total_gain(self):
        """Test PortfolioSummary.total_gain property."""
        summary = PortfolioSummary(
            total_contributions=5000.0,
            total_withdrawals=1000.0,
            current_value=5500.0,
            start_date=TEST_DATE_1,
            end_date=TEST_DATE_2,
        )

        # total_gain = current_value + withdrawals - contributions
        # 5500 + 1000 - 5000 = 1500
        assert summary.total_gain == 1500.0

    def test_portfolio_summary_simple_return(self):
        """Test PortfolioSummary.simple_return property."""
        summary = PortfolioSummary(
            total_contributions=5000.0,
            total_withdrawals=1000.0,
            current_value=5500.0,
            start_date=TEST_DATE_1,
            end_date=TEST_DATE_2,
        )

        # simple_return = (total_gain / contributions) * 100
        # (1500 / 5000) * 100 = 30%
        assert summary.simple_return == 30.0

    def test_portfolio_summary_simple_return_zero_contributions(self):
        """Test PortfolioSummary.simple_return with zero contributions."""
        summary = PortfolioSummary(
            total_contributions=0.0,
            total_withdrawals=0.0,
            current_value=1000.0,
            start_date=TEST_DATE_1,
            end_date=TEST_DATE_2,
        )

        assert summary.simple_return == 0.0

    def test_portfolio_summary_years_invested(self):
        """Test PortfolioSummary.years_invested property."""
        summary = PortfolioSummary(
            total_contributions=5000.0,
            total_withdrawals=0.0,
            current_value=5500.0,
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
        )

        assert summary.years_invested == pytest.approx(1.0, abs=0.01)
