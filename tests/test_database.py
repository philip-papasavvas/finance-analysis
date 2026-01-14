"""Unit tests for portfolio/core/database.py database operations."""


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


class TestDatabaseInsertTransaction:
    """Test transaction insertion operations."""

    def test_insert_single_transaction(self, in_memory_db):
        """Test inserting a single transaction."""
        transaction = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=float(TEST_UNITS_1),
            price_per_unit=float(TEST_PRICE_1),
            value=float(TEST_AMOUNT_1),
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
        )

        result = in_memory_db.insert_transaction(transaction)
        assert result is True

        # Verify insertion (note: get_all_transactions returns dicts, not Transaction objects)
        all_transactions = in_memory_db.get_all_transactions()
        assert len(all_transactions) == 1
        assert all_transactions[0]["fund_name"] == TEST_FUND_NAME_1

    def test_insert_duplicate_transaction(self, in_memory_db):
        """Test inserting duplicate transaction with same reference returns False."""
        # Create two transactions with matching fields including reference
        transaction1 = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=float(TEST_UNITS_1),
            price_per_unit=float(TEST_PRICE_1),
            value=float(TEST_AMOUNT_1),
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
            reference="REF-001",  # Set reference for duplicate detection
        )
        transaction2 = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=float(TEST_UNITS_1),
            price_per_unit=float(TEST_PRICE_1),
            value=float(TEST_AMOUNT_1),
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
            reference="REF-001",  # Same reference for duplicate detection
        )

        # Insert first transaction
        result1 = in_memory_db.insert_transaction(transaction1)
        assert result1 is True

        # Try inserting duplicate (same platform, date, fund_name, type, value, reference)
        result2 = in_memory_db.insert_transaction(transaction2)
        assert result2 is False

        # Verify only one transaction exists
        all_transactions = in_memory_db.get_all_transactions()
        assert len(all_transactions) == 1

    def test_insert_multiple_transactions(self, in_memory_db):
        """Test inserting multiple distinct transactions."""
        transaction1 = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=float(TEST_UNITS_1),
            price_per_unit=float(TEST_PRICE_1),
            value=float(TEST_AMOUNT_1),
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
        )
        transaction2 = Transaction(
            date=TEST_DATE_2,
            fund_name=TEST_FUND_NAME_2,
            transaction_type=TransactionType.SELL,
            units=float(TEST_UNITS_2),
            price_per_unit=float(TEST_PRICE_2),
            value=float(TEST_AMOUNT_2),
            platform=TEST_PLATFORM_II,
            tax_wrapper=TEST_WRAPPER_SIPP,
        )

        result1 = in_memory_db.insert_transaction(transaction1)
        result2 = in_memory_db.insert_transaction(transaction2)

        assert result1 is True
        assert result2 is True
        assert len(in_memory_db.get_all_transactions()) == 2

    def test_insert_transactions_batch(self, in_memory_db):
        """Test batch transaction insertion."""
        transactions = [
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

        inserted, duplicates = in_memory_db.insert_transactions(transactions)
        assert inserted == 2
        assert duplicates == 0
        assert len(in_memory_db.get_all_transactions()) == 2

    def test_insert_transactions_with_duplicates(self, in_memory_db):
        """Test batch insertion handles duplicates correctly."""
        transaction1 = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=float(TEST_UNITS_1),
            price_per_unit=float(TEST_PRICE_1),
            value=float(TEST_AMOUNT_1),
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
            reference="REF-DUP",
        )

        # Insert first transaction
        in_memory_db.insert_transaction(transaction1)

        # Try batch insertion with exact duplicate (same reference)
        transaction2 = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=float(TEST_UNITS_1),
            price_per_unit=float(TEST_PRICE_1),
            value=float(TEST_AMOUNT_1),
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
            reference="REF-DUP",  # Same reference
        )
        transactions = [transaction2]
        inserted, duplicates = in_memory_db.insert_transactions(transactions)
        assert inserted == 0
        assert duplicates == 1


class TestDatabaseGetTransactionsByFund:
    """Test fund-based transaction retrieval."""

    def test_get_transactions_by_fund_exact_match(self, populated_db):
        """Test retrieving transactions by exact fund name."""
        results = populated_db.get_transactions_by_fund(TEST_FUND_NAME_1)
        assert len(results) == 1
        assert results[0]["fund_name"] == TEST_FUND_NAME_1

    def test_get_transactions_by_fund_partial_match(self, populated_db):
        """Test retrieving transactions by partial fund name (LIKE pattern)."""
        results = populated_db.get_transactions_by_fund("FTSE")
        assert len(results) == 1
        assert "FTSE" in results[0]["fund_name"]

    def test_get_transactions_by_fund_no_match(self, populated_db):
        """Test retrieving transactions with no matching fund."""
        results = populated_db.get_transactions_by_fund("NonexistentFund")
        assert len(results) == 0

    def test_get_transactions_by_fund_case_insensitive(self, populated_db):
        """Test fund name matching is case-insensitive."""
        results = populated_db.get_transactions_by_fund("vanguard")
        assert len(results) == 1

    def test_get_transactions_by_fund_multiple_matches(self, in_memory_db):
        """Test retrieving multiple transactions for same fund."""
        # Insert two transactions for same fund
        tx1 = Transaction(
            date=TEST_DATE_1,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.BUY,
            units=float(TEST_UNITS_1),
            price_per_unit=float(TEST_PRICE_1),
            value=float(TEST_AMOUNT_1),
            platform=TEST_PLATFORM_FIDELITY,
            tax_wrapper=TEST_WRAPPER_ISA,
        )
        tx2 = Transaction(
            date=TEST_DATE_2,
            fund_name=TEST_FUND_NAME_1,
            transaction_type=TransactionType.SELL,
            units=float(TEST_UNITS_2),
            price_per_unit=float(TEST_PRICE_2),
            value=float(TEST_AMOUNT_2),
            platform=TEST_PLATFORM_II,
            tax_wrapper=TEST_WRAPPER_SIPP,
        )
        in_memory_db.insert_transaction(tx1)
        in_memory_db.insert_transaction(tx2)

        results = in_memory_db.get_transactions_by_fund(TEST_FUND_NAME_1)
        assert len(results) == 2


class TestDatabaseGetTransactionsByDateRange:
    """Test date range filtering."""

    def test_get_transactions_by_date_range(self, populated_db):
        """Test retrieving transactions within date range."""
        results = populated_db.get_transactions_by_date_range(TEST_DATE_1, TEST_DATE_2)
        assert len(results) == 2

    def test_get_transactions_by_date_range_no_matches(self, populated_db):
        """Test date range with no matching transactions."""
        from datetime import date

        results = populated_db.get_transactions_by_date_range(date(2020, 1, 1), date(2020, 12, 31))
        assert len(results) == 0

    def test_get_transactions_by_date_range_single_date(self, populated_db):
        """Test date range with single matching date."""
        results = populated_db.get_transactions_by_date_range(TEST_DATE_1, TEST_DATE_1)
        assert len(results) == 1


class TestDatabasePriceHistory:
    """Test price history operations."""

    def test_insert_price_history(self, in_memory_db):
        """Test inserting price history."""
        result = in_memory_db.insert_price_history(
            TEST_DATE_1.strftime("%Y-%m-%d"),  # date in YYYY-MM-DD format
            TEST_TICKER_1,  # ticker
            TEST_FUND_NAME_1,  # fund_name
            float(TEST_PRICE_1),  # close_price
        )
        assert result is True

    def test_insert_duplicate_price_history(self, in_memory_db):
        """Test inserting duplicate price history returns False."""
        in_memory_db.insert_price_history(
            TEST_DATE_1.strftime("%Y-%m-%d"),
            TEST_TICKER_1,
            TEST_FUND_NAME_1,
            float(TEST_PRICE_1),
        )
        result = in_memory_db.insert_price_history(
            TEST_DATE_1.strftime("%Y-%m-%d"),
            TEST_TICKER_1,
            TEST_FUND_NAME_1,
            float(TEST_PRICE_1),
        )
        assert result is False

    def test_insert_price_histories_batch(self, in_memory_db):
        """Test batch price history insertion."""
        prices = [
            {
                "date": TEST_DATE_1.strftime("%Y-%m-%d"),
                "ticker": TEST_TICKER_1,
                "fund_name": TEST_FUND_NAME_1,
                "close_price": float(TEST_PRICE_1),
            },
            {
                "date": TEST_DATE_2.strftime("%Y-%m-%d"),
                "ticker": TEST_TICKER_2,
                "fund_name": TEST_FUND_NAME_2,
                "close_price": float(TEST_PRICE_2),
            },
        ]
        inserted, duplicates = in_memory_db.insert_price_histories(prices)
        assert inserted == 2
        assert duplicates == 0


class TestDatabaseTickerMapping:
    """Test fund-to-ticker mapping operations."""

    def test_add_fund_ticker_mapping(self, in_memory_db):
        """Test adding fund-to-ticker mapping."""
        result = in_memory_db.add_fund_ticker_mapping(TEST_FUND_NAME_1, TEST_TICKER_1)
        assert result is True

    def test_add_duplicate_fund_ticker_mapping(self, in_memory_db):
        """Test adding duplicate mapping returns False."""
        in_memory_db.add_fund_ticker_mapping(TEST_FUND_NAME_1, TEST_TICKER_1)
        result = in_memory_db.add_fund_ticker_mapping(TEST_FUND_NAME_1, TEST_TICKER_1)
        assert result is False

    def test_get_ticker_for_fund(self, populated_db):
        """Test retrieving ticker for fund."""
        ticker = populated_db.get_ticker_for_fund(TEST_FUND_NAME_1)
        assert ticker == TEST_TICKER_1

    def test_get_ticker_for_nonexistent_fund(self, populated_db):
        """Test retrieving ticker for nonexistent fund."""
        ticker = populated_db.get_ticker_for_fund("NonexistentFund")
        assert ticker is None

    def test_get_all_fund_ticker_mappings(self, populated_db):
        """Test retrieving all fund-ticker mappings."""
        mappings = populated_db.get_all_fund_ticker_mappings()
        assert len(mappings) == 2
        fund_names = [m["fund_name"] for m in mappings]
        assert TEST_FUND_NAME_1 in fund_names
        assert TEST_FUND_NAME_2 in fund_names


class TestDatabaseUtilityMethods:
    """Test utility methods."""

    def test_get_all_transactions(self, populated_db):
        """Test retrieving all transactions."""
        results = populated_db.get_all_transactions()
        assert len(results) == 2

    def test_get_unique_funds(self, populated_db):
        """Test retrieving unique fund names."""
        funds = populated_db.get_unique_funds()
        assert TEST_FUND_NAME_1 in funds
        assert TEST_FUND_NAME_2 in funds
        assert len(funds) >= 2

    def test_get_all_price_tickers(self, populated_db):
        """Test retrieving all price tickers."""
        tickers = populated_db.get_all_price_tickers()
        assert TEST_TICKER_1 in tickers
        assert TEST_TICKER_2 in tickers

    def test_get_summary_stats(self, populated_db):
        """Test retrieving summary statistics."""
        stats = populated_db.get_summary_stats()
        assert stats is not None
        assert "total_transactions" in stats
        assert stats["total_transactions"] == 2

    def test_set_mapped_fund_name(self, populated_db):
        """Test setting mapped fund name."""
        new_name = "Updated Fund Name"
        # set_mapped_fund_name doesn't return anything, just updates the database
        populated_db.set_mapped_fund_name(TEST_FUND_NAME_1, new_name)

        # Verify the mapped name was updated
        transactions = populated_db.get_transactions_by_fund(TEST_FUND_NAME_1)
        assert transactions[0]["mapped_fund_name"] == new_name
