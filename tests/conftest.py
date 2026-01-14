"""Shared pytest fixtures and configuration."""

import json
from io import StringIO
from unittest.mock import Mock

import pandas as pd
import pytest

from portfolio.core.database import TransactionDatabase
from portfolio.core.models import Transaction, TransactionType
from tests.fixtures.test_data import (
    TEST_DATE_1,
    TEST_DATE_2,
    TEST_TICKER_1,
    TEST_TICKER_2,
    TEST_AMOUNT_1,
    TEST_AMOUNT_2,
    TEST_UNITS_1,
    TEST_UNITS_2,
    TEST_PRICE_1,
    TEST_PRICE_2,
    TEST_FUND_NAME_1,
    TEST_FUND_NAME_2,
    TEST_PLATFORM_FIDELITY,
    TEST_PLATFORM_II,
    TEST_WRAPPER_ISA,
    TEST_WRAPPER_SIPP,
)


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture
def in_memory_db():
    """Create a fresh in-memory SQLite database for each test."""
    db = TransactionDatabase(":memory:")
    yield db
    db.close()


@pytest.fixture
def populated_db(in_memory_db):
    """Create a populated in-memory database with sample data."""
    # Insert sample transactions
    transaction_1 = Transaction(
        date=TEST_DATE_1,
        fund_name=TEST_FUND_NAME_1,
        transaction_type=TransactionType.BUY,
        units=float(TEST_UNITS_1),
        price_per_unit=float(TEST_PRICE_1),
        value=float(TEST_AMOUNT_1),
        platform=TEST_PLATFORM_FIDELITY,
        tax_wrapper=TEST_WRAPPER_ISA,
    )
    transaction_2 = Transaction(
        date=TEST_DATE_2,
        fund_name=TEST_FUND_NAME_2,
        transaction_type=TransactionType.SELL,
        units=float(TEST_UNITS_2),
        price_per_unit=float(TEST_PRICE_2),
        value=float(TEST_AMOUNT_2),
        platform=TEST_PLATFORM_II,
        tax_wrapper=TEST_WRAPPER_SIPP,
    )

    in_memory_db.insert_transaction(transaction_1)
    in_memory_db.insert_transaction(transaction_2)

    # Add ticker mappings
    in_memory_db.add_fund_ticker_mapping(TEST_FUND_NAME_1, TEST_TICKER_1)
    in_memory_db.add_fund_ticker_mapping(TEST_FUND_NAME_2, TEST_TICKER_2)

    # Insert price history (signature: date, ticker, fund_name, close_price)
    # Date must be in YYYY-MM-DD format
    in_memory_db.insert_price_history(
        TEST_DATE_1.strftime("%Y-%m-%d"),
        TEST_TICKER_1,
        TEST_FUND_NAME_1,
        float(TEST_PRICE_1),
    )
    in_memory_db.insert_price_history(
        TEST_DATE_2.strftime("%Y-%m-%d"),
        TEST_TICKER_2,
        TEST_FUND_NAME_2,
        float(TEST_PRICE_2),
    )

    return in_memory_db


# ============================================================================
# TRANSACTION FIXTURES
# ============================================================================


@pytest.fixture
def sample_transaction():
    """Create a sample Transaction object for testing."""
    return Transaction(
        date=TEST_DATE_1,
        fund_name=TEST_FUND_NAME_1,
        transaction_type=TransactionType.BUY,
        units=float(TEST_UNITS_1),
        price_per_unit=float(TEST_PRICE_1),
        value=float(TEST_AMOUNT_1),
        platform=TEST_PLATFORM_FIDELITY,
        tax_wrapper=TEST_WRAPPER_ISA,
    )


@pytest.fixture
def sample_transactions_list():
    """Create a list of sample Transaction objects."""
    return [
        Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=float(TEST_UNITS_1),
            price_per_unit=float(TEST_PRICE_1),
            value=float(TEST_AMOUNT_1),
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
        ),
        Transaction(
            date=TEST_DATE_2,
            fund_name=TEST_FUND_NAME_2,
            transaction_type=TransactionType.SELL,
            units=float(TEST_UNITS_2),
            price_per_unit=float(TEST_PRICE_2),
            value=float(TEST_AMOUNT_2),
            platform=TEST_PLATFORM_II,
            tax_wrapper=TEST_WRAPPER_SIPP,
        ),
    ]


# ============================================================================
# CSV FIXTURES
# ============================================================================


@pytest.fixture
def fidelity_csv_sample():
    """Create sample Fidelity CSV data as StringIO."""
    csv_content = """Date,Account,Description,Units,Amount,Status
15/01/2024,ISA,Buy - Vanguard FTSE All-World Index Fund,100.00,£1000.00,Completed
20/02/2024,SIPP,Sell - iShares Core MSCI World UCITS ETF,250.50,£2500.50,Completed
"""
    return StringIO(csv_content)


@pytest.fixture
def ii_csv_sample():
    """Create sample Interactive Investor CSV data as StringIO."""
    csv_content = """Date,Description,Debit,Credit,SEDOL
15/01/2024,Vanguard FTSE All-World Index Fund,1000.00,,0000001
20/02/2024,iShares Core MSCI World UCITS ETF,,2500.50,0000002
"""
    return StringIO(csv_content)


@pytest.fixture
def ie_csv_sample():
    """Create sample InvestEngine CSV data as StringIO."""
    csv_content = """Date,Fund Name,Quantity,Price,Type
15/01/2024,Vanguard FTSE All-World Index Fund,100.00,10.50,Buy
20/02/2024,iShares Core MSCI World UCITS ETF,250.50,25.75,Sell
"""
    return StringIO(csv_content)


# ============================================================================
# YFINANCE MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_yfinance_ticker():
    """Create a mock yfinance Ticker object."""
    mock_ticker = Mock()

    # Mock price history DataFrame
    price_data = pd.DataFrame(
        {
            "Close": [100.0, 101.0, 102.0],
        },
        index=pd.date_range(start=TEST_DATE_1, periods=3),
    )
    mock_ticker.history.return_value = price_data

    return mock_ticker


@pytest.fixture
def mock_yfinance_forex(mocker):
    """Create a mock for forex pair (e.g., GBPUSD=X)."""
    mock_ticker = Mock()

    # Mock a forex price
    price_data = pd.DataFrame(
        {
            "Close": [1.2640, 1.2645, 1.2650],
        },
        index=pd.date_range(start=TEST_DATE_1, periods=3),
    )
    mock_ticker.history.return_value = price_data

    return mock_ticker


@pytest.fixture
def patch_yfinance_ticker(mocker):
    """Patch yfinance.Ticker to return mock ticker."""
    mock_ticker = Mock()
    price_data = pd.DataFrame(
        {
            "Close": [100.0, 101.0, 102.0],
        },
        index=pd.date_range(start=TEST_DATE_1, periods=3),
    )
    mock_ticker.history.return_value = price_data

    mocker.patch("yfinance.Ticker", return_value=mock_ticker)
    return mock_ticker


# ============================================================================
# JSON/FILE FIXTURES
# ============================================================================


@pytest.fixture
def sample_current_holdings_json():
    """Create sample current_holdings.json data."""
    return {
        TEST_TICKER_1: {
            "fund_name": TEST_FUND_NAME_1,
            "holdings": [
                {
                    "platform": TEST_PLATFORM_FIDELITY,
                    "tax_wrapper": TEST_WRAPPER_ISA,
                    "units": str(TEST_UNITS_1),
                }
            ],
        },
        TEST_TICKER_2: {
            "fund_name": TEST_FUND_NAME_2,
            "holdings": [
                {
                    "platform": TEST_PLATFORM_II,
                    "tax_wrapper": TEST_WRAPPER_SIPP,
                    "units": str(TEST_UNITS_2),
                }
            ],
        },
    }


@pytest.fixture
def mock_current_holdings_file(mocker, sample_current_holdings_json, tmp_path):
    """Mock reading current_holdings.json file."""
    mock_file = tmp_path / "current_holdings.json"
    mock_file.write_text(json.dumps(sample_current_holdings_json))

    mocker.patch(
        "builtins.open",
        mocker.mock_open(read_data=json.dumps(sample_current_holdings_json)),
    )
    return sample_current_holdings_json


# ============================================================================
# DATAFRAME FIXTURES
# ============================================================================


@pytest.fixture
def sample_price_dataframe():
    """Create a sample price history DataFrame."""
    return pd.DataFrame(
        {
            "Close": [100.0, 101.0, 102.0, 103.0],
        },
        index=pd.date_range(start=TEST_DATE_1, periods=4),
    )


@pytest.fixture
def sample_holdings_dataframe():
    """Create a sample holdings DataFrame."""
    return pd.DataFrame(
        {
            "ticker": [TEST_TICKER_1, TEST_TICKER_1, TEST_TICKER_2],
            "fund_name": [TEST_FUND_NAME_1, TEST_FUND_NAME_1, TEST_FUND_NAME_2],
            "platform": [TEST_PLATFORM_FIDELITY, TEST_PLATFORM_II, TEST_PLATFORM_FIDELITY],
            "tax_wrapper": [TEST_WRAPPER_ISA, TEST_WRAPPER_SIPP, TEST_WRAPPER_ISA],
            "units": [100.0, 50.0, 75.5],
            "price": [10.50, 10.50, 25.75],
            "price_date": [TEST_DATE_1, TEST_DATE_1, TEST_DATE_2],
        }
    )


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
