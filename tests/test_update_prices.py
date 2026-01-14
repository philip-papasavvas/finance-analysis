"""Unit tests for scripts/update_prices.py price updater."""

from datetime import date

import pandas as pd

from scripts.update_prices import PriceUpdater, UpdateResult, UpdateReport
from tests.fixtures.test_data import (
    TEST_TICKER_1,
    TEST_TICKER_2,
    TEST_PRICE_1,
    TEST_FUND_NAME_1,
    TEST_FUND_NAME_2,
)


class TestUpdateResult:
    """Test UpdateResult dataclass."""

    def test_update_result_creation(self):
        """Test creating an UpdateResult."""
        result = UpdateResult(
            ticker=TEST_TICKER_1,
            fund_name=TEST_FUND_NAME_1,
            records_fetched=10,
            records_inserted=8,
            records_skipped=2,
            missing_dates_found=5,
            success=True,
        )

        assert result.ticker == TEST_TICKER_1
        assert result.fund_name == TEST_FUND_NAME_1
        assert result.records_fetched == 10
        assert result.records_inserted == 8
        assert result.records_skipped == 2
        assert result.missing_dates_found == 5
        assert result.success is True


class TestUpdateReport:
    """Test UpdateReport dataclass."""

    def test_update_report_creation(self):
        """Test creating an UpdateReport."""
        results = [
            UpdateResult(TEST_TICKER_1, TEST_FUND_NAME_1, records_inserted=10, success=True),
            UpdateResult(TEST_TICKER_2, TEST_FUND_NAME_2, records_inserted=0, success=False),
        ]

        report = UpdateReport(results=results, dry_run=False)

        # Report properties are calculated from results list
        assert len(report.results) == 2
        assert report.successful_tickers == 1
        assert report.failed_tickers == 1
        assert report.total_inserted == 10
        assert report.dry_run is False


class TestPriceUpdaterTradingDays:
    """Test trading day calculation."""

    def test_get_trading_days_weekdays_only(self, tmp_path, mocker):
        """Test that trading days excludes weekends."""
        # Create temporary database file
        db_file = tmp_path / "test.db"
        db_file.touch()

        updater = PriceUpdater(db_file, dry_run=True)

        # Calculate trading days for a week with weekends
        # Monday 2024-01-15 to Friday 2024-01-19
        start = date(2024, 1, 15)  # Monday
        end = date(2024, 1, 19)  # Friday

        trading_days = updater.get_trading_days(start, end)

        # Should have 5 weekdays, no weekends (returns set of date strings)
        assert len(trading_days) == 5
        # Verify all dates are ISO format strings
        assert all(isinstance(d, str) for d in trading_days)

    def test_get_trading_days_excludes_weekends(self, tmp_path):
        """Test that weekends are excluded."""
        db_file = tmp_path / "test.db"
        db_file.touch()

        updater = PriceUpdater(db_file, dry_run=True)

        # Friday 2024-01-19 to Monday 2024-01-22
        start = date(2024, 1, 19)  # Friday
        end = date(2024, 1, 22)  # Monday

        trading_days = updater.get_trading_days(start, end)

        # Should have 2 trading days (Fri, Mon) - weekend excluded
        assert len(trading_days) == 2
        # Convert strings to dates for weekday checking
        for day_str in trading_days:
            day_obj = date.fromisoformat(day_str)
            assert day_obj.weekday() < 5  # Weekday

    def test_get_trading_days_single_day(self, tmp_path):
        """Test trading days for a single day."""
        db_file = tmp_path / "test.db"
        db_file.touch()

        updater = PriceUpdater(db_file, dry_run=True)

        # Monday - should be included
        day = date(2024, 1, 15)
        trading_days = updater.get_trading_days(day, day)

        assert len(trading_days) == 1
        assert day.isoformat() in trading_days


class TestPriceUpdaterMissingDates:
    """Test missing date detection."""

    def test_find_missing_dates_empty_history(self, tmp_path, mocker):
        """Test missing dates when no history exists."""
        db_file = tmp_path / "test.db"
        db_file.touch()

        updater = PriceUpdater(db_file, dry_run=True)

        # Mock get_existing_dates to return empty set
        updater.get_existing_dates = mocker.MagicMock(return_value=set())

        # get_trading_days returns set of ISO strings
        expected_days = {"2024-01-15", "2024-01-16"}
        updater.get_trading_days = mocker.MagicMock(return_value=expected_days)

        missing = updater.find_missing_dates(TEST_TICKER_1, date(2024, 1, 15), date(2024, 1, 16))

        # All expected days should be missing
        assert len(missing) == 2
        assert "2024-01-15" in missing

    def test_find_missing_dates_partial_history(self, tmp_path, mocker):
        """Test missing dates when some history exists."""
        db_file = tmp_path / "test.db"
        db_file.touch()

        updater = PriceUpdater(db_file, dry_run=True)

        # Mock get_existing_dates to return one existing date (as set of strings)
        existing = {"2024-01-15"}
        updater.get_existing_dates = mocker.MagicMock(return_value=existing)

        # get_trading_days returns set of ISO strings
        expected_days = {"2024-01-15", "2024-01-16", "2024-01-17"}
        updater.get_trading_days = mocker.MagicMock(return_value=expected_days)

        missing = updater.find_missing_dates(TEST_TICKER_1, date(2024, 1, 15), date(2024, 1, 17))

        # Only the missing dates should be returned
        assert len(missing) == 2
        assert "2024-01-15" not in missing
        assert "2024-01-16" in missing
        assert "2024-01-17" in missing


class TestPriceUpdaterParsing:
    """Test price data parsing."""

    def test_parse_price_data_valid_dataframe(self, tmp_path):
        """Test parsing valid price data."""
        db_file = tmp_path / "test.db"
        db_file.touch()

        updater = PriceUpdater(db_file, dry_run=True)

        # Create mock price data
        df = pd.DataFrame(
            {
                "Close": [10.5, 10.6, 10.7],
            }
        )
        df.index = pd.to_datetime(["2024-01-15", "2024-01-16", "2024-01-17"])

        records = updater.parse_price_data(df, TEST_TICKER_1, TEST_FUND_NAME_1)

        assert len(records) == 3
        assert records[0]["ticker"] == TEST_TICKER_1
        assert records[0]["fund_name"] == TEST_FUND_NAME_1
        assert "date" in records[0]
        assert "close_price" in records[0]

    def test_parse_price_data_filters_negative_prices(self, tmp_path):
        """Test that negative prices are filtered."""
        db_file = tmp_path / "test.db"
        db_file.touch()

        updater = PriceUpdater(db_file, dry_run=True)

        df = pd.DataFrame(
            {
                "Close": [10.5, -10.6, 10.7],
            }
        )
        df.index = pd.to_datetime(["2024-01-15", "2024-01-16", "2024-01-17"])

        records = updater.parse_price_data(df, TEST_TICKER_1, TEST_FUND_NAME_1)

        # Should only have 2 records (negative price filtered out)
        assert len(records) == 2


class TestPriceUpdaterDryRun:
    """Test dry-run mode."""

    def test_dry_run_no_insert(self, tmp_path):
        """Test that dry-run mode doesn't insert records."""
        db_file = tmp_path / "test.db"
        db_file.touch()

        updater = PriceUpdater(db_file, dry_run=True)

        # Create mock records to insert
        records = [
            {
                "date": "2024-01-15",
                "ticker": TEST_TICKER_1,
                "fund_name": TEST_FUND_NAME_1,
                "close_price": float(TEST_PRICE_1),
            }
        ]

        # In dry-run mode, nothing should be inserted
        inserted, skipped = updater.insert_prices(records)

        # In dry-run mode, all records should be skipped (treated as duplicates)
        assert updater.dry_run is True
        assert inserted == 0
        assert skipped == len(records)
