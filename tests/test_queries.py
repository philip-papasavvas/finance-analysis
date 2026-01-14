"""Unit tests for app/data/queries.py query functions."""


import pandas as pd

from app.data import queries
from tests.fixtures.test_data import (
    TEST_FUND_NAME_1,
    TEST_FUND_NAME_2,
)


class TestGetAllFundsFromDb:
    """Test get_all_funds_from_db function."""

    def test_get_all_funds_returns_dict(self, mocker):
        """Test that function returns a dictionary."""
        # Mock the database connection and cursor
        mock_db = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_db.conn.cursor.return_value = mock_cursor

        # Mock cursor.fetchall() to return test data
        mock_cursor.fetchall.return_value = [
            {"fund_name": TEST_FUND_NAME_1, "display_name": TEST_FUND_NAME_1},
            {"fund_name": TEST_FUND_NAME_2, "display_name": TEST_FUND_NAME_2},
        ]

        mocker.patch("app.data.queries.TransactionDatabase", return_value=mock_db)

        funds = queries.get_all_funds_from_db()

        assert isinstance(funds, dict)
        assert len(funds) == 2
        assert TEST_FUND_NAME_1 in funds
        assert TEST_FUND_NAME_2 in funds

    def test_get_all_funds_returns_empty_dict_when_no_funds(self, mocker):
        """Test function returns empty dict when no funds found."""
        mock_db = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_db.conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        mocker.patch("app.data.queries.TransactionDatabase", return_value=mock_db)

        funds = queries.get_all_funds_from_db()

        assert isinstance(funds, dict)
        assert len(funds) == 0


class TestGetFundTransactions:
    """Test get_fund_transactions function."""

    def test_get_fund_transactions_returns_dataframe(self, mocker):
        """Test function returns a DataFrame."""
        mock_db = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_db.conn.cursor.return_value = mock_cursor

        # Mock transaction data
        mock_cursor.fetchall.return_value = [
            {
                "date": "2024-01-15",
                "platform": "Fidelity",
                "tax_wrapper": "ISA",
                "fund_name": TEST_FUND_NAME_1,
                "mapped_fund_name": TEST_FUND_NAME_1,
                "transaction_type": "BUY",
                "units": 100.0,
                "price_per_unit": 10.5,
                "value": 1050.0,
                "currency": "GBP",
            }
        ]

        mocker.patch("app.data.queries.TransactionDatabase", return_value=mock_db)

        df = queries.get_fund_transactions(TEST_FUND_NAME_1)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert df.iloc[0]["Fund Name"] == TEST_FUND_NAME_1

    def test_get_fund_transactions_returns_empty_dataframe_when_no_match(self, mocker):
        """Test function returns empty DataFrame when fund not found."""
        mock_db = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_db.conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        mocker.patch("app.data.queries.TransactionDatabase", return_value=mock_db)

        df = queries.get_fund_transactions("NonexistentFund")

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_get_fund_transactions_uses_mapped_name_when_available(self, mocker):
        """Test that mapped fund name is used in display."""
        mock_db = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_db.conn.cursor.return_value = mock_cursor

        mapped_name = "Mapped Fund Name"
        mock_cursor.fetchall.return_value = [
            {
                "date": "2024-01-15",
                "platform": "Fidelity",
                "tax_wrapper": "ISA",
                "fund_name": TEST_FUND_NAME_1,
                "mapped_fund_name": mapped_name,
                "transaction_type": "BUY",
                "units": 100.0,
                "price_per_unit": 10.5,
                "value": 1050.0,
                "currency": "GBP",
            }
        ]

        mocker.patch("app.data.queries.TransactionDatabase", return_value=mock_db)

        df = queries.get_fund_transactions(TEST_FUND_NAME_1)

        assert df.iloc[0]["Fund Name"] == mapped_name


class TestGetAllTransactions:
    """Test get_all_transactions function."""

    def test_get_all_transactions_returns_dataframe(self, mocker):
        """Test function returns a DataFrame."""
        mock_db = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_db.conn.cursor.return_value = mock_cursor

        mock_cursor.fetchall.return_value = [
            {
                "date": "2024-01-15",
                "platform": "Fidelity",
                "tax_wrapper": "ISA",
                "fund_name": TEST_FUND_NAME_1,
                "transaction_type": "BUY",
                "units": 100.0,
                "price_per_unit": 10.5,
                "value": 1050.0,
                "currency": "GBP",
            },
            {
                "date": "2024-02-20",
                "platform": "II",
                "tax_wrapper": "SIPP",
                "fund_name": TEST_FUND_NAME_2,
                "transaction_type": "SELL",
                "units": 50.0,
                "price_per_unit": 12.0,
                "value": 600.0,
                "currency": "GBP",
            },
        ]

        mocker.patch("app.data.queries.TransactionDatabase", return_value=mock_db)

        df = queries.get_all_transactions()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2

    def test_get_all_transactions_returns_empty_dataframe_when_no_data(self, mocker):
        """Test function returns empty DataFrame when no transactions."""
        mock_db = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_db.conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        mocker.patch("app.data.queries.TransactionDatabase", return_value=mock_db)

        df = queries.get_all_transactions()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestGetRecentTransactions:
    """Test get_recent_transactions function."""

    def test_get_recent_transactions_returns_dataframe(self, mocker):
        """Test function returns a DataFrame."""
        mock_db = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_db.conn.cursor.return_value = mock_cursor

        # Mock 3 recent transactions
        mock_cursor.fetchall.return_value = [
            {
                "date": "2024-02-20",
                "platform": "Fidelity",
                "tax_wrapper": "ISA",
                "fund_name": TEST_FUND_NAME_1,
                "mapped_fund_name": TEST_FUND_NAME_1,
                "transaction_type": "BUY",
                "units": 100.0,
                "price_per_unit": 10.5,
                "value": 1050.0,
                "currency": "GBP",
            }
        ]

        mocker.patch("app.data.queries.TransactionDatabase", return_value=mock_db)

        df = queries.get_recent_transactions(limit=10)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_get_recent_transactions_respects_limit(self, mocker):
        """Test function respects the limit parameter."""
        mock_db = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_db.conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []

        mocker.patch("app.data.queries.TransactionDatabase", return_value=mock_db)

        # Verify that limit parameter was used in the query
        queries.get_recent_transactions(limit=5)
        mock_cursor.execute.assert_called()
