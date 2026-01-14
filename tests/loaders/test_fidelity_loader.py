"""Unit tests for Fidelity CSV loader."""

from pathlib import Path

import pandas as pd

from portfolio.core.models import TaxWrapper, TransactionType
from portfolio.loaders.fidelity import FidelityLoader
from tests.fixtures.test_data import (
    TEST_FUND_NAME_1,
    TEST_AMOUNT_1,
    TEST_UNITS_1,
    TEST_PRICE_1,
)


class TestFidelityLoaderRowParsing:
    """Test Fidelity CSV row parsing."""

    def test_parse_buy_transaction(self):
        """Test parsing a buy transaction row."""
        loader = FidelityLoader(Path("/tmp"))

        row = pd.Series(
            {
                "Order date": "15/01/2024",
                "Investments": TEST_FUND_NAME_1,
                "Transaction type": "Buy",
                "Quantity": float(TEST_UNITS_1),
                "Price per unit": float(TEST_PRICE_1),
                "Amount": f"£{float(TEST_AMOUNT_1)}",
                "Product Wrapper": "ISA",
                "Sedol": "1234567",
                "Reference number": "REF-001",
            }
        )

        transaction = loader._parse_row(row)

        assert transaction is not None
        assert transaction.transaction_type == TransactionType.BUY
        assert transaction.fund_name == TEST_FUND_NAME_1
        assert transaction.units == float(TEST_UNITS_1)
        assert transaction.tax_wrapper == TaxWrapper.ISA

    def test_parse_sell_transaction(self):
        """Test parsing a sell transaction row."""
        loader = FidelityLoader(Path("/tmp"))

        row = pd.Series(
            {
                "Order date": "15/01/2024",
                "Investments": TEST_FUND_NAME_1,
                "Transaction type": "Sell",
                "Quantity": "100.00",
                "Price per unit": "10.50",
                "Amount": "£1050.00",
                "Product Wrapper": "SIPP",
                "Sedol": "1234567",
                "Reference number": "REF-002",
            }
        )

        transaction = loader._parse_row(row)

        assert transaction is not None
        assert transaction.transaction_type == TransactionType.SELL
        assert transaction.tax_wrapper == TaxWrapper.SIPP

    def test_parse_row_with_zero_units(self):
        """Test that rows with zero units are skipped."""
        loader = FidelityLoader(Path("/tmp"))

        row = pd.Series(
            {
                "Order date": "15/01/2024",
                "Investments": TEST_FUND_NAME_1,
                "Transaction type": "Buy",
                "Quantity": "0.00",
                "Price per unit": "10.50",
                "Amount": "£0.00",
                "Product Wrapper": "ISA",
            }
        )

        transaction = loader._parse_row(row)
        assert transaction is None

    def test_parse_row_with_invalid_date(self):
        """Test that rows with invalid dates are skipped."""
        loader = FidelityLoader(Path("/tmp"))

        row = pd.Series(
            {
                "Order date": "invalid-date",
                "Investments": TEST_FUND_NAME_1,
                "Transaction type": "Buy",
                "Quantity": "100",
                "Price per unit": "10.50",
                "Amount": "£1050.00",
                "Product Wrapper": "ISA",
            }
        )

        transaction = loader._parse_row(row)
        assert transaction is None

    def test_parse_row_with_non_buy_sell(self):
        """Test that non-buy/sell transactions are skipped."""
        loader = FidelityLoader(Path("/tmp"))

        row = pd.Series(
            {
                "Order date": "15/01/2024",
                "Investments": TEST_FUND_NAME_1,
                "Transaction type": "Dividend",
                "Quantity": "100",
                "Price per unit": "10.50",
                "Amount": "£100.00",
                "Product Wrapper": "ISA",
            }
        )

        transaction = loader._parse_row(row)
        assert transaction is None


class TestFidelityLoaderTaxWrapperDetection:
    """Test Fidelity tax wrapper determination."""

    def test_determine_tax_wrapper_isa(self):
        """Test ISA detection."""
        loader = FidelityLoader(Path("/tmp"))
        row = pd.Series({"Product Wrapper": "ISA"})

        wrapper = loader._determine_tax_wrapper(row)
        assert wrapper == TaxWrapper.ISA

    def test_determine_tax_wrapper_sipp(self):
        """Test SIPP detection."""
        loader = FidelityLoader(Path("/tmp"))
        row = pd.Series({"Product Wrapper": "SIPP"})

        wrapper = loader._determine_tax_wrapper(row)
        assert wrapper == TaxWrapper.SIPP

    def test_determine_tax_wrapper_other(self):
        """Test fallback to OTHER."""
        loader = FidelityLoader(Path("/tmp"))
        row = pd.Series({"Product Wrapper": "GIA"})

        wrapper = loader._determine_tax_wrapper(row)
        assert wrapper == TaxWrapper.OTHER

    def test_determine_tax_wrapper_case_insensitive(self):
        """Test case-insensitive matching."""
        loader = FidelityLoader(Path("/tmp"))
        row = pd.Series({"Product Wrapper": "isa"})

        wrapper = loader._determine_tax_wrapper(row)
        assert wrapper == TaxWrapper.ISA


class TestFidelityLoaderTransactionTypeDetection:
    """Test Fidelity transaction type determination."""

    def test_determine_transaction_type_buy(self):
        """Test BUY detection."""
        loader = FidelityLoader(Path("/tmp"))
        row = pd.Series({"Transaction type": "Buy"})

        tx_type = loader._determine_transaction_type(row)
        assert tx_type == TransactionType.BUY

    def test_determine_transaction_type_buy_for_switch(self):
        """Test Buy For Switch detection."""
        loader = FidelityLoader(Path("/tmp"))
        row = pd.Series({"Transaction type": "Buy For Switch"})

        tx_type = loader._determine_transaction_type(row)
        assert tx_type == TransactionType.BUY

    def test_determine_transaction_type_transfer_in(self):
        """Test Transfer In detection."""
        loader = FidelityLoader(Path("/tmp"))
        row = pd.Series({"Transaction type": "Transfer In"})

        tx_type = loader._determine_transaction_type(row)
        assert tx_type == TransactionType.BUY

    def test_determine_transaction_type_sell(self):
        """Test SELL detection."""
        loader = FidelityLoader(Path("/tmp"))
        row = pd.Series({"Transaction type": "Sell"})

        tx_type = loader._determine_transaction_type(row)
        assert tx_type == TransactionType.SELL

    def test_determine_transaction_type_sell_for_switch(self):
        """Test Sell For Switch detection."""
        loader = FidelityLoader(Path("/tmp"))
        row = pd.Series({"Transaction type": "Sell For Switch"})

        tx_type = loader._determine_transaction_type(row)
        assert tx_type == TransactionType.SELL

    def test_determine_transaction_type_other(self):
        """Test fallback to OTHER."""
        loader = FidelityLoader(Path("/tmp"))
        row = pd.Series({"Transaction type": "Dividend"})

        tx_type = loader._determine_transaction_type(row)
        assert tx_type == TransactionType.OTHER


class TestFidelityLoaderLoad:
    """Test Fidelity loader load() method with mocked files."""

    def test_load_empty_directory(self, tmp_path, mocker):
        """Test loading from empty directory."""
        # Mock find_csv_files to return empty list
        mocker.patch("portfolio.loaders.fidelity.find_csv_files", return_value=[])

        loader = FidelityLoader(tmp_path)
        transactions = loader.load()

        assert transactions == []

    def test_load_parses_csv_correctly(self, tmp_path, mocker):
        """Test that load() correctly parses valid CSV data."""
        # Create a mock CSV file path
        csv_file = tmp_path / "TransactionHistory.csv"

        # Mock find_csv_files to return our test file
        mocker.patch("portfolio.loaders.fidelity.find_csv_files", return_value=[csv_file])

        # Mock pd.read_csv to return test data
        test_df = pd.DataFrame(
            {
                "Order date": ["15/01/2024", "20/02/2024"],
                "Investments": [TEST_FUND_NAME_1, "Another Fund"],
                "Transaction type": ["Buy", "Sell"],
                "Quantity": [100.0, 50.0],
                "Price per unit": [10.5, 12.0],
                "Amount": ["1050.00", "600.00"],
                "Product Wrapper": ["ISA", "SIPP"],
                "Sedol": ["1234567", "7654321"],
                "Reference number": ["REF-001", "REF-002"],
                "Status": ["Completed", "Completed"],
            }
        )

        mocker.patch("pandas.read_csv", return_value=test_df)

        loader = FidelityLoader(tmp_path)
        transactions = loader.load()

        # Should have parsed 2 transactions
        assert len(transactions) == 2
        assert transactions[0].transaction_type == TransactionType.BUY
        assert transactions[1].transaction_type == TransactionType.SELL
