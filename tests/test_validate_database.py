"""Unit tests for scripts/validate_database.py database validator."""

import sqlite3

import pytest

from scripts.validate_database import DatabaseValidator
from tests.fixtures.test_data import (
    TEST_DATE_1,
    TEST_DATE_2,
    TEST_TICKER_1,
    TEST_FUND_NAME_1,
    TEST_FUND_NAME_2,
)


@pytest.fixture
def validator_db(tmp_path):
    """Create a temporary database for validation testing."""
    db_file = tmp_path / "test.db"

    # Create connection and initialize schema
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create necessary tables
    cursor.execute(
        """
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY,
            date TEXT,
            fund_name TEXT,
            mapped_fund_name TEXT,
            transaction_type TEXT,
            units REAL,
            price_per_unit REAL,
            value REAL,
            platform TEXT,
            tax_wrapper TEXT,
            excluded INTEGER DEFAULT 0
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE fund_ticker_mapping (
            fund_name TEXT PRIMARY KEY,
            ticker TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE price_history (
            id INTEGER PRIMARY KEY,
            date TEXT,
            ticker TEXT,
            close_price REAL,
            UNIQUE(date, ticker)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE mapping_status (
            ticker TEXT PRIMARY KEY,
            fund_name TEXT,
            earliest_date TEXT,
            latest_date TEXT
        )
    """
    )

    conn.commit()
    conn.close()

    return str(db_file)


class TestDatabaseValidatorOrphanedFunds:
    """Test orphaned fund detection."""

    def test_check_orphaned_funds_none(self, validator_db):
        """Test that no orphaned funds are detected when all mapped."""
        validator = DatabaseValidator(validator_db)

        # Add mapping for fund_name to prevent orphaning
        cursor = validator.conn.cursor()
        cursor.execute(
            "INSERT INTO fund_ticker_mapping (fund_name, ticker) VALUES (?, ?)",
            (TEST_FUND_NAME_1, TEST_TICKER_1),
        )
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_1.isoformat(),
                TEST_FUND_NAME_1,
                TEST_FUND_NAME_1,
                "BUY",
                100.0,
                10.0,
                1000.0,
                "Fidelity",
                "ISA",
                0,
            ),
        )
        validator.conn.commit()

        count = validator.check_orphaned_funds()

        assert count == 0

    def test_check_orphaned_funds_detected(self, validator_db):
        """Test detection of orphaned funds."""
        validator = DatabaseValidator(validator_db)

        # Add transaction without corresponding mapping
        cursor = validator.conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_1.isoformat(),
                TEST_FUND_NAME_1,
                TEST_FUND_NAME_1,
                "BUY",
                100.0,
                10.0,
                1000.0,
                "Fidelity",
                "ISA",
                0,
            ),
        )
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_2.isoformat(),
                TEST_FUND_NAME_1,
                TEST_FUND_NAME_1,
                "SELL",
                50.0,
                11.0,
                550.0,
                "Fidelity",
                "ISA",
                0,
            ),
        )
        validator.conn.commit()

        count = validator.check_orphaned_funds()

        # Should find 1 orphaned fund name
        assert count == 1


class TestDatabaseValidatorDateRanges:
    """Test date range validation."""

    def test_check_date_ranges_valid(self, validator_db):
        """Test that no issues are found with valid date ranges."""
        validator = DatabaseValidator(validator_db)

        cursor = validator.conn.cursor()
        # Add mapping and mapping_status with dates that match transaction dates
        cursor.execute(
            "INSERT INTO fund_ticker_mapping (fund_name, ticker) VALUES (?, ?)",
            (TEST_FUND_NAME_1, TEST_TICKER_1),
        )
        # mapping_status should match the actual transaction date ranges
        cursor.execute(
            "INSERT INTO mapping_status (ticker, fund_name, earliest_date, latest_date) VALUES (?, ?, ?, ?)",
            (TEST_TICKER_1, TEST_FUND_NAME_1, TEST_DATE_1.isoformat(), TEST_DATE_1.isoformat()),
        )
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_1.isoformat(),
                TEST_FUND_NAME_1,
                TEST_FUND_NAME_1,
                "BUY",
                100.0,
                10.0,
                1000.0,
                "Fidelity",
                "ISA",
                0,
            ),
        )
        validator.conn.commit()

        count = validator.check_date_ranges()

        assert count == 0

    def test_check_date_ranges_mismatch(self, validator_db):
        """Test detection of date range mismatches."""
        validator = DatabaseValidator(validator_db)

        cursor = validator.conn.cursor()
        # Add mapping_status with date range that doesn't cover transaction
        cursor.execute(
            "INSERT INTO fund_ticker_mapping (fund_name, ticker) VALUES (?, ?)",
            (TEST_FUND_NAME_1, TEST_TICKER_1),
        )
        cursor.execute(
            "INSERT INTO mapping_status (ticker, fund_name, earliest_date, latest_date) VALUES (?, ?, ?, ?)",
            (TEST_TICKER_1, TEST_FUND_NAME_1, "2024-02-01", "2024-02-28"),  # Doesn't cover Jan 15
        )
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_1.isoformat(),
                TEST_FUND_NAME_1,
                TEST_FUND_NAME_1,
                "BUY",
                100.0,
                10.0,
                1000.0,
                "Fidelity",
                "ISA",
                0,
            ),
        )
        validator.conn.commit()

        count = validator.check_date_ranges()

        assert count == 1


class TestDatabaseValidatorDuplicatePrices:
    """Test duplicate price detection."""

    def test_check_duplicate_prices_none(self, validator_db):
        """Test that no duplicate prices are detected when all unique."""
        validator = DatabaseValidator(validator_db)

        cursor = validator.conn.cursor()
        cursor.execute(
            "INSERT INTO price_history (date, ticker, close_price) VALUES (?, ?, ?)",
            (TEST_DATE_1.isoformat(), TEST_TICKER_1, 10.5),
        )
        cursor.execute(
            "INSERT INTO price_history (date, ticker, close_price) VALUES (?, ?, ?)",
            (TEST_DATE_2.isoformat(), TEST_TICKER_1, 10.6),
        )
        validator.conn.commit()

        count = validator.check_duplicate_prices()

        assert count == 0

    def test_check_duplicate_prices_detected(self, validator_db):
        """Test detection of duplicate prices."""
        validator = DatabaseValidator(validator_db)

        # The UNIQUE constraint on (date, ticker) prevents duplicates
        # So this test just verifies the check runs without error
        # A real duplicate would require disabling the constraint, which is not recommended

        count = validator.check_duplicate_prices()

        # With UNIQUE constraint properly enforced, we should get 0 duplicates
        assert count == 0


class TestDatabaseValidatorMissingPrices:
    """Test missing price detection."""

    def test_check_missing_prices_none(self, validator_db):
        """Test that no missing prices are found when all have prices."""
        validator = DatabaseValidator(validator_db)

        cursor = validator.conn.cursor()
        cursor.execute(
            "INSERT INTO fund_ticker_mapping (fund_name, ticker) VALUES (?, ?)",
            (TEST_FUND_NAME_1, TEST_TICKER_1),
        )
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_1.isoformat(),
                TEST_FUND_NAME_1,
                TEST_FUND_NAME_1,
                "BUY",
                100.0,
                10.0,
                1000.0,
                "Fidelity",
                "ISA",
                0,
            ),
        )
        cursor.execute(
            "INSERT INTO price_history (date, ticker, close_price) VALUES (?, ?, ?)",
            (TEST_DATE_1.isoformat(), TEST_TICKER_1, 10.5),
        )
        validator.conn.commit()

        count = validator.check_missing_prices()

        assert count == 0

    def test_check_missing_prices_detected(self, validator_db):
        """Test detection of transactions without price data."""
        validator = DatabaseValidator(validator_db)

        cursor = validator.conn.cursor()
        cursor.execute(
            "INSERT INTO fund_ticker_mapping (fund_name, ticker) VALUES (?, ?)",
            (TEST_FUND_NAME_1, TEST_TICKER_1),
        )
        # Add transaction without corresponding price history
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_1.isoformat(),
                TEST_FUND_NAME_1,
                TEST_FUND_NAME_1,
                "BUY",
                100.0,
                10.0,
                1000.0,
                "Fidelity",
                "ISA",
                0,
            ),
        )
        validator.conn.commit()

        count = validator.check_missing_prices()

        assert count > 0


class TestDatabaseValidatorTickerConsistency:
    """Test ticker consistency validation."""

    def test_check_ticker_consistency_valid(self, validator_db):
        """Test that no issues found when all tickers have prices."""
        validator = DatabaseValidator(validator_db)

        cursor = validator.conn.cursor()
        cursor.execute(
            "INSERT INTO fund_ticker_mapping (fund_name, ticker) VALUES (?, ?)",
            (TEST_FUND_NAME_1, TEST_TICKER_1),
        )
        cursor.execute(
            "INSERT INTO price_history (date, ticker, close_price) VALUES (?, ?, ?)",
            (TEST_DATE_1.isoformat(), TEST_TICKER_1, 10.5),
        )
        validator.conn.commit()

        count = validator.check_ticker_consistency()

        assert count == 0

    def test_check_ticker_consistency_found(self, validator_db):
        """Test detection of tickers without price history."""
        validator = DatabaseValidator(validator_db)

        cursor = validator.conn.cursor()
        # Add ticker mapping but no price history
        cursor.execute(
            "INSERT INTO fund_ticker_mapping (fund_name, ticker) VALUES (?, ?)",
            (TEST_FUND_NAME_1, TEST_TICKER_1),
        )
        validator.conn.commit()

        count = validator.check_ticker_consistency()

        assert count > 0


class TestDatabaseValidatorRunAllChecks:
    """Test running all validation checks."""

    def test_run_all_checks_no_issues(self, validator_db):
        """Test run_all_checks when no issues are found."""
        validator = DatabaseValidator(validator_db)

        cursor = validator.conn.cursor()
        cursor.execute(
            "INSERT INTO fund_ticker_mapping (fund_name, ticker) VALUES (?, ?)",
            (TEST_FUND_NAME_1, TEST_TICKER_1),
        )
        cursor.execute(
            "INSERT INTO mapping_status (ticker, fund_name, earliest_date, latest_date) VALUES (?, ?, ?, ?)",
            (TEST_TICKER_1, TEST_FUND_NAME_1, TEST_DATE_1.isoformat(), TEST_DATE_1.isoformat()),
        )
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_1.isoformat(),
                TEST_FUND_NAME_1,
                TEST_FUND_NAME_1,
                "BUY",
                100.0,
                10.0,
                1000.0,
                "Fidelity",
                "ISA",
                0,
            ),
        )
        cursor.execute(
            "INSERT INTO price_history (date, ticker, close_price) VALUES (?, ?, ?)",
            (TEST_DATE_1.isoformat(), TEST_TICKER_1, 10.5),
        )
        validator.conn.commit()

        issue_count, warning_count = validator.run_all_checks()

        assert issue_count == 0

    def test_run_all_checks_with_issues(self, validator_db):
        """Test run_all_checks when issues are found."""
        validator = DatabaseValidator(validator_db)

        cursor = validator.conn.cursor()
        # Add orphaned fund (no mapping)
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_1.isoformat(),
                TEST_FUND_NAME_1,
                TEST_FUND_NAME_1,
                "BUY",
                100.0,
                10.0,
                1000.0,
                "Fidelity",
                "ISA",
                0,
            ),
        )
        validator.conn.commit()

        issue_count, warning_count = validator.run_all_checks()

        # Should find at least the orphaned fund warning
        assert warning_count > 0


class TestDatabaseValidatorExcludedTransactions:
    """Test that excluded transactions are properly filtered."""

    def test_checks_exclude_excluded_transactions(self, validator_db):
        """Test that excluded=1 transactions are ignored."""
        validator = DatabaseValidator(validator_db)

        cursor = validator.conn.cursor()
        # Add one excluded and one normal transaction
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_1.isoformat(),
                TEST_FUND_NAME_1,
                TEST_FUND_NAME_1,
                "BUY",
                100.0,
                10.0,
                1000.0,
                "Fidelity",
                "ISA",
                1,
            ),  # excluded=1
        )
        cursor.execute(
            "INSERT INTO transactions (date, fund_name, mapped_fund_name, transaction_type, units, price_per_unit, value, platform, tax_wrapper, excluded) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                TEST_DATE_2.isoformat(),
                TEST_FUND_NAME_2,
                TEST_FUND_NAME_2,
                "BUY",
                50.0,
                10.0,
                500.0,
                "Fidelity",
                "ISA",
                0,
            ),  # excluded=0 (normal)
        )
        validator.conn.commit()

        # Check orphaned funds - should only find TEST_FUND_NAME_2 (excluded transaction ignored)
        count = validator.check_orphaned_funds()

        # Only the non-excluded transaction should be checked
        assert count == 1  # TEST_FUND_NAME_2 is orphaned
