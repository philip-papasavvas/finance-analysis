#!/usr/bin/env python3
"""
Price Data Management Script for Portfolio Analyzer.

Features:
- Dynamic price updates with date range parameters (1.1)
- One-off historical backfill capability (1.2)
- CLI interface with dry-run mode and ticker selection (1.3)

Usage:
    # Update all tickers for missing dates in the last 30 days
    python scripts/update_prices.py

    # Update specific date range
    python scripts/update_prices.py --min-date 2024-01-01 --max-date 2024-12-31

    # Update specific tickers only
    python scripts/update_prices.py --tickers SUUS.L SMT.L

    # Backfill historical data
    python scripts/update_prices.py --backfill --min-date 2019-01-01

    # Dry run (preview without changes)
    python scripts/update_prices.py --dry-run

    # Verbose output
    python scripts/update_prices.py -v
"""
import argparse
import logging
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import TransactionDatabase

# Attempt to import yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# Constants
DB_PATH = Path(__file__).parent.parent / "portfolio.db"
DEFAULT_START_DATE = "2019-01-01"
RATE_LIMIT_DELAY = 0.5  # Seconds between API calls
MAX_RETRIES = 3
RETRY_DELAY = 5  # Seconds between retries


@dataclass
class UpdateResult:
    """Result of a price update operation."""
    ticker: str
    fund_name: str
    records_fetched: int = 0
    records_inserted: int = 0
    records_skipped: int = 0
    missing_dates_found: int = 0
    errors: list[str] = field(default_factory=list)
    success: bool = True


@dataclass
class UpdateReport:
    """Summary report of all update operations."""
    results: list[UpdateResult] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    dry_run: bool = False

    @property
    def total_fetched(self) -> int:
        return sum(r.records_fetched for r in self.results)

    @property
    def total_inserted(self) -> int:
        return sum(r.records_inserted for r in self.results)

    @property
    def total_skipped(self) -> int:
        return sum(r.records_skipped for r in self.results)

    @property
    def successful_tickers(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed_tickers(self) -> int:
        return sum(1 for r in self.results if not r.success)

    def print_summary(self, logger: logging.Logger) -> None:
        """Print a summary of the update report."""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        logger.info("")
        logger.info("=" * 70)
        logger.info("PRICE UPDATE REPORT")
        logger.info("=" * 70)

        if self.dry_run:
            logger.info("*** DRY RUN - No changes were made ***")
            logger.info("")

        logger.info(f"Duration: {duration:.1f} seconds")
        logger.info(f"Tickers processed: {len(self.results)}")
        logger.info(f"  - Successful: {self.successful_tickers}")
        logger.info(f"  - Failed: {self.failed_tickers}")
        logger.info("")
        logger.info(f"Records fetched: {self.total_fetched}")
        logger.info(f"Records inserted: {self.total_inserted}")
        logger.info(f"Records skipped (duplicates): {self.total_skipped}")
        logger.info("")

        # Per-ticker summary
        logger.info("Per-Ticker Summary:")
        logger.info("-" * 70)
        for result in self.results:
            status = "✓" if result.success else "✗"
            logger.info(
                f"  {status} {result.ticker}: "
                f"fetched={result.records_fetched}, "
                f"inserted={result.records_inserted}, "
                f"skipped={result.records_skipped}"
            )
            if result.errors:
                for error in result.errors:
                    logger.error(f"      Error: {error}")

        logger.info("=" * 70)


class PriceUpdater:
    """Manages price data updates from Yahoo Finance."""

    def __init__(
        self,
        db_path: Path = DB_PATH,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the price updater.

        Args:
            db_path: Path to SQLite database
            dry_run: If True, preview changes without committing
            verbose: If True, enable debug logging
        """
        self.db_path = db_path
        self.dry_run = dry_run
        self.verbose = verbose
        self.logger = self._setup_logging()
        self.db: Optional[TransactionDatabase] = None

        if not YFINANCE_AVAILABLE:
            self.logger.error("yfinance is not installed. Run: pip install yfinance")
            sys.exit(1)

    def _setup_logging(self) -> logging.Logger:
        """Configure logging."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
        )
        return logging.getLogger(__name__)

    def connect(self) -> None:
        """Connect to the database."""
        if not self.db_path.exists():
            self.logger.error(f"Database not found: {self.db_path}")
            sys.exit(1)
        self.db = TransactionDatabase(str(self.db_path))
        self.logger.debug(f"Connected to database: {self.db_path}")

    def close(self) -> None:
        """Close database connection."""
        if self.db:
            self.db.close()
            self.logger.debug("Database connection closed")

    def get_all_tickers(self) -> list[tuple[str, str]]:
        """
        Get all tickers from fund_ticker_mapping.

        Returns:
            List of (ticker, fund_name) tuples
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT ticker, fund_name
            FROM fund_ticker_mapping
            ORDER BY ticker
        """)
        return [(row["ticker"], row["fund_name"]) for row in cursor.fetchall()]

    def get_existing_dates(self, ticker: str) -> set[str]:
        """
        Get all dates with existing price data for a ticker.

        Args:
            ticker: Ticker symbol

        Returns:
            Set of date strings (YYYY-MM-DD)
        """
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT date FROM price_history
            WHERE ticker = ?
        """, (ticker,))
        return {row["date"] for row in cursor.fetchall()}

    def get_trading_days(self, start_date: date, end_date: date) -> set[str]:
        """
        Get expected trading days between dates (weekdays only).

        Note: This is a simple approximation - doesn't account for holidays.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Set of date strings (YYYY-MM-DD) for weekdays
        """
        trading_days = set()
        current = start_date
        while current <= end_date:
            # Monday = 0, Sunday = 6
            if current.weekday() < 5:  # Weekday
                trading_days.add(current.isoformat())
            current += timedelta(days=1)
        return trading_days

    def find_missing_dates(
        self,
        ticker: str,
        min_date: date,
        max_date: date,
    ) -> list[str]:
        """
        Find dates missing price data for a ticker.

        Args:
            ticker: Ticker symbol
            min_date: Start of date range
            max_date: End of date range

        Returns:
            Sorted list of missing date strings
        """
        existing = self.get_existing_dates(ticker)
        expected = self.get_trading_days(min_date, max_date)
        missing = expected - existing
        return sorted(missing)

    def download_prices(
        self,
        ticker: str,
        start_date: str,
        end_date: str,
        retries: int = MAX_RETRIES,
    ) -> pd.DataFrame:
        """
        Download price data from Yahoo Finance with retry logic.

        Args:
            ticker: Ticker symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            retries: Number of retry attempts

        Returns:
            DataFrame with price data
        """
        for attempt in range(retries):
            try:
                self.logger.debug(f"Downloading {ticker} ({start_date} to {end_date})...")
                data = yf.download(
                    ticker,
                    start=start_date,
                    end=end_date,
                    progress=False,
                    auto_adjust=False,
                )

                if len(data) > 0:
                    return data

                self.logger.warning(f"No data returned for {ticker}")
                return pd.DataFrame()

            except Exception as e:
                self.logger.warning(
                    f"Attempt {attempt + 1}/{retries} failed for {ticker}: {e}"
                )
                if attempt < retries - 1:
                    time.sleep(RETRY_DELAY)

        self.logger.error(f"All retries failed for {ticker}")
        return pd.DataFrame()

    def parse_price_data(
        self,
        data: pd.DataFrame,
        ticker: str,
        fund_name: str,
    ) -> list[dict]:
        """
        Parse downloaded price data into records.

        Args:
            data: DataFrame from yfinance
            ticker: Ticker symbol
            fund_name: Fund name for reference

        Returns:
            List of price record dictionaries
        """
        records = []
        for date_idx, row in data.iterrows():
            try:
                # Handle both single-column and multi-column DataFrame formats
                close_val = row["Close"]
                if hasattr(close_val, 'iloc'):
                    close_price = float(close_val.iloc[0])
                else:
                    close_price = float(close_val)
                if close_price > 0:
                    records.append({
                        "date": date_idx.strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "fund_name": fund_name,
                        "close_price": close_price,
                    })
            except (ValueError, TypeError, KeyError):
                continue
        return records

    def insert_prices(self, records: list[dict]) -> tuple[int, int]:
        """
        Insert price records into database.

        Args:
            records: List of price record dictionaries

        Returns:
            Tuple of (inserted_count, duplicate_count)
        """
        if self.dry_run or not records:
            return 0, len(records)

        return self.db.insert_price_histories(records)

    def update_ticker(
        self,
        ticker: str,
        fund_name: str,
        min_date: date,
        max_date: date,
        backfill: bool = False,
    ) -> UpdateResult:
        """
        Update price data for a single ticker.

        Args:
            ticker: Ticker symbol
            fund_name: Fund name
            min_date: Start of date range
            max_date: End of date range
            backfill: If True, fetch full date range regardless of existing data

        Returns:
            UpdateResult with operation details
        """
        result = UpdateResult(ticker=ticker, fund_name=fund_name)

        try:
            # Find missing dates
            if backfill:
                # For backfill, we fetch the full range
                result.missing_dates_found = (max_date - min_date).days
                start_str = min_date.isoformat()
                end_str = (max_date + timedelta(days=1)).isoformat()
            else:
                missing = self.find_missing_dates(ticker, min_date, max_date)
                result.missing_dates_found = len(missing)

                if not missing:
                    self.logger.info(f"  {ticker}: No missing dates in range")
                    return result

                # Use the full range to minimize API calls
                start_str = min_date.isoformat()
                end_str = (max_date + timedelta(days=1)).isoformat()

            self.logger.info(
                f"  {ticker}: Fetching {start_str} to {max_date.isoformat()}..."
            )

            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)

            # Download data
            data = self.download_prices(ticker, start_str, end_str)

            if data.empty:
                result.errors.append("No data returned from Yahoo Finance")
                result.success = False
                return result

            # Parse records
            records = self.parse_price_data(data, ticker, fund_name)
            result.records_fetched = len(records)

            if self.dry_run:
                self.logger.info(
                    f"  {ticker}: Would insert {len(records)} records (dry run)"
                )
                result.records_skipped = len(records)
            else:
                # Insert into database
                inserted, skipped = self.insert_prices(records)
                result.records_inserted = inserted
                result.records_skipped = skipped
                self.logger.info(
                    f"  {ticker}: Inserted {inserted}, skipped {skipped} duplicates"
                )

        except Exception as e:
            result.errors.append(str(e))
            result.success = False
            self.logger.error(f"  {ticker}: Error - {e}")

        return result

    def update_all(
        self,
        tickers: Optional[list[str]] = None,
        min_date: Optional[date] = None,
        max_date: Optional[date] = None,
        backfill: bool = False,
    ) -> UpdateReport:
        """
        Update price data for multiple tickers.

        Args:
            tickers: List of tickers to update (None = all)
            min_date: Start of date range (None = 30 days ago)
            max_date: End of date range (None = today)
            backfill: If True, fetch full date range

        Returns:
            UpdateReport with all results
        """
        report = UpdateReport(dry_run=self.dry_run)

        # Default date range
        if max_date is None:
            max_date = date.today()
        if min_date is None:
            min_date = max_date - timedelta(days=30)

        self.logger.info("=" * 70)
        self.logger.info("PRICE DATA UPDATE")
        self.logger.info("=" * 70)

        if self.dry_run:
            self.logger.info("*** DRY RUN MODE - No changes will be made ***")

        self.logger.info(f"Date range: {min_date} to {max_date}")
        self.logger.info(f"Backfill mode: {'Yes' if backfill else 'No'}")
        self.logger.info("")

        # Get tickers to update
        all_tickers = self.get_all_tickers()

        if tickers:
            # Filter to requested tickers
            ticker_set = set(tickers)
            all_tickers = [(t, f) for t, f in all_tickers if t in ticker_set]

            # Warn about unknown tickers
            known = {t for t, _ in all_tickers}
            unknown = ticker_set - known
            if unknown:
                self.logger.warning(f"Unknown tickers (skipped): {unknown}")

        if not all_tickers:
            self.logger.warning("No tickers to update")
            return report

        self.logger.info(f"Updating {len(all_tickers)} ticker(s):")
        for ticker, fund_name in all_tickers:
            self.logger.info(f"  - {ticker} ({fund_name})")
        self.logger.info("")

        # Process each ticker with progress
        for i, (ticker, fund_name) in enumerate(all_tickers, 1):
            self.logger.info(f"[{i}/{len(all_tickers)}] Processing {ticker}...")
            result = self.update_ticker(
                ticker=ticker,
                fund_name=fund_name,
                min_date=min_date,
                max_date=max_date,
                backfill=backfill,
            )
            report.results.append(result)

        return report


def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: {date_str}. Use YYYY-MM-DD."
        )


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Update price data for portfolio tickers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update all tickers for the last 30 days
  python scripts/update_prices.py

  # Update specific date range
  python scripts/update_prices.py --min-date 2024-01-01 --max-date 2024-12-31

  # Update specific tickers
  python scripts/update_prices.py --tickers SUUS.L SMT.L

  # Full historical backfill
  python scripts/update_prices.py --backfill --min-date 2019-01-01

  # Preview changes without committing
  python scripts/update_prices.py --dry-run
        """,
    )

    parser.add_argument(
        "--min-date",
        type=parse_date,
        help="Start date (YYYY-MM-DD). Default: 30 days ago",
    )
    parser.add_argument(
        "--max-date",
        type=parse_date,
        help="End date (YYYY-MM-DD). Default: today",
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        help="Specific tickers to update. Default: all mapped tickers",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Full historical backfill (ignores existing data)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without committing to database",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug output",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DB_PATH,
        help=f"Path to database. Default: {DB_PATH}",
    )

    args = parser.parse_args()

    # Create updater
    updater = PriceUpdater(
        db_path=args.db_path,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    try:
        updater.connect()

        # Run update
        report = updater.update_all(
            tickers=args.tickers,
            min_date=args.min_date,
            max_date=args.max_date,
            backfill=args.backfill,
        )

        # Print report
        report.print_summary(updater.logger)

        # Exit code based on success
        sys.exit(0 if report.failed_tickers == 0 else 1)

    finally:
        updater.close()


if __name__ == "__main__":
    # Usage Examples:
    #
    #   python scripts/update_prices.py                           # Last 30 days
    #   python scripts/update_prices.py --dry-run                 # Preview
    #   python scripts/update_prices.py --backfill --min-date 2019-01-01
    #   python scripts/update_prices.py --tickers SMT.L SUUS.L

    main()
