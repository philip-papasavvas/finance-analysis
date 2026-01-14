"""
Database validation script for portfolio analyzer.

Checks for data integrity issues including:
- Orphaned funds (transactions without ticker mappings)
- Date range validation against mapping_status
- Duplicate price records
- Missing price data for transaction dates
- Ticker consistency across tables

Usage:
    python src/validate_database.py [--db-path portfolio.db]
"""
import argparse
import logging
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)

logger = logging.getLogger(__name__)


class DatabaseValidator:
    """Validates database integrity for portfolio data."""

    def __init__(self, db_path: str | Path):
        """Initialize validator with database path."""
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.issues: list[dict] = []
        self.warnings: list[dict] = []

    def _add_issue(self, check: str, message: str, details: list | None = None) -> None:
        """Record an issue found during validation."""
        self.issues.append({"check": check, "message": message, "details": details or []})

    def _add_warning(self, check: str, message: str, details: list | None = None) -> None:
        """Record a warning (non-critical issue)."""
        self.warnings.append({"check": check, "message": message, "details": details or []})

    def check_orphaned_funds(self) -> int:
        """
        Check for transactions with no corresponding ticker mapping.

        Returns count of orphaned fund names.
        """
        logger.info("Checking for orphaned funds (no ticker mapping)...")
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT t.fund_name, COUNT(*) as tx_count
            FROM transactions t
            LEFT JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            WHERE ftm.fund_name IS NULL
              AND t.excluded = 0
            GROUP BY t.fund_name
            ORDER BY tx_count DESC
        """
        )

        orphans = cursor.fetchall()
        if orphans:
            details = [f"{row['fund_name']} ({row['tx_count']} transactions)" for row in orphans]
            self._add_warning(
                "orphaned_funds", f"Found {len(orphans)} funds without ticker mappings", details
            )
            return len(orphans)

        logger.info("  ✓ No orphaned funds found")
        return 0

    def check_date_ranges(self) -> int:
        """
        Verify transaction dates against mapping_status ranges.

        Returns count of date mismatches.
        """
        logger.info("Checking transaction dates vs mapping_status...")
        cursor = self.conn.cursor()

        # Check if mapping_status table exists
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='mapping_status'
        """
        )
        if not cursor.fetchone():
            logger.info("  ⊘ mapping_status table doesn't exist, skipping check")
            return 0

        cursor.execute(
            """
            SELECT
                ms.ticker,
                ms.fund_name,
                ms.earliest_date as status_earliest,
                ms.latest_date as status_latest,
                MIN(t.date) as actual_earliest,
                MAX(t.date) as actual_latest,
                COUNT(t.id) as tx_count
            FROM mapping_status ms
            JOIN fund_ticker_mapping ftm ON ms.ticker = ftm.ticker
            JOIN transactions t ON (t.fund_name = ftm.fund_name OR t.mapped_fund_name = ftm.fund_name)
            WHERE t.excluded = 0
            GROUP BY ms.ticker
            HAVING actual_earliest != status_earliest OR actual_latest != status_latest
        """
        )

        mismatches = cursor.fetchall()
        if mismatches:
            details = [
                f"{row['ticker']}: status={row['status_earliest']}→{row['status_latest']}, "
                f"actual={row['actual_earliest']}→{row['actual_latest']}"
                for row in mismatches
            ]
            self._add_warning(
                "date_range_mismatch",
                f"Found {len(mismatches)} tickers with outdated mapping_status dates",
                details,
            )
            return len(mismatches)

        logger.info("  ✓ All mapping_status date ranges are accurate")
        return 0

    def check_duplicate_prices(self) -> int:
        """
        Check for duplicate price records (same date+ticker).

        Returns count of duplicates found.
        """
        logger.info("Checking for duplicate price records...")
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT date, ticker, COUNT(*) as count
            FROM price_history
            GROUP BY date, ticker
            HAVING count > 1
        """
        )

        duplicates = cursor.fetchall()
        if duplicates:
            details = [
                f"{row['date']} {row['ticker']}: {row['count']} records" for row in duplicates
            ]
            self._add_issue(
                "duplicate_prices", f"Found {len(duplicates)} duplicate price entries", details
            )
            return len(duplicates)

        logger.info("  ✓ No duplicate price records found")
        return 0

    def check_missing_prices(self) -> int:
        """
        Check for funds with transactions but no price data on transaction dates.

        Returns count of missing price records.
        """
        logger.info("Checking for missing price data on transaction dates...")
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                ftm.ticker,
                t.date,
                t.fund_name,
                t.transaction_type
            FROM transactions t
            JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            LEFT JOIN price_history ph ON ftm.ticker = ph.ticker AND t.date = ph.date
            WHERE ph.id IS NULL
              AND t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
            ORDER BY ftm.ticker, t.date
        """
        )

        missing = cursor.fetchall()
        if missing:
            # Group by ticker for cleaner output
            by_ticker: dict[str, list[str]] = {}
            for row in missing:
                ticker = row["ticker"]
                if ticker not in by_ticker:
                    by_ticker[ticker] = []
                by_ticker[ticker].append(row["date"])

            details = [
                f"{ticker}: missing {len(dates)} dates" for ticker, dates in by_ticker.items()
            ]
            self._add_warning(
                "missing_prices",
                f"Found {len(missing)} transactions without corresponding price data",
                details,
            )
            return len(missing)

        logger.info("  ✓ All transactions have corresponding price data")
        return 0

    def check_ticker_consistency(self) -> int:
        """
        Check that all tickers in fund_ticker_mapping have price_history data.

        Returns count of tickers with no price data.
        """
        logger.info("Checking ticker consistency (mappings vs price_history)...")
        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT ftm.ticker, ftm.fund_name
            FROM fund_ticker_mapping ftm
            LEFT JOIN price_history ph ON ftm.ticker = ph.ticker
            WHERE ph.id IS NULL
        """
        )

        missing_tickers = cursor.fetchall()
        if missing_tickers:
            details = [f"{row['ticker']} ({row['fund_name']})" for row in missing_tickers]
            self._add_issue(
                "missing_ticker_prices",
                f"Found {len(missing_tickers)} tickers with no price history",
                details,
            )
            return len(missing_tickers)

        logger.info("  ✓ All mapped tickers have price data")
        return 0

    def run_all_checks(self) -> tuple[int, int]:
        """
        Run all validation checks.

        Returns tuple of (issue_count, warning_count).
        """
        logger.info("=" * 60)
        logger.info("DATABASE VALIDATION")
        logger.info("=" * 60)
        logger.info(f"Database: {self.db_path}")
        logger.info("")

        self.check_orphaned_funds()
        self.check_date_ranges()
        self.check_duplicate_prices()
        self.check_missing_prices()
        self.check_ticker_consistency()

        return len(self.issues), len(self.warnings)

    def print_report(self) -> None:
        """Print validation report."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("VALIDATION REPORT")
        logger.info("=" * 60)

        if self.issues:
            logger.error(f"✗ {len(self.issues)} ISSUE(S) FOUND:")
            for issue in self.issues:
                logger.error(f"  [{issue['check']}] {issue['message']}")
                for detail in issue["details"][:5]:  # Show first 5 details
                    logger.error(f"    - {detail}")
                if len(issue["details"]) > 5:
                    logger.error(f"    ... and {len(issue['details']) - 5} more")
        else:
            logger.info("✓ No critical issues found")

        logger.info("")

        if self.warnings:
            logger.warning(f"⚠ {len(self.warnings)} WARNING(S):")
            for warning in self.warnings:
                logger.warning(f"  [{warning['check']}] {warning['message']}")
                for detail in warning["details"][:5]:  # Show first 5 details
                    logger.warning(f"    - {detail}")
                if len(warning["details"]) > 5:
                    logger.warning(f"    ... and {len(warning['details']) - 5} more")
        else:
            logger.info("✓ No warnings")

        logger.info("")
        logger.info("=" * 60)

        if self.issues:
            logger.error("RESULT: FAILED - Critical issues need attention")
        elif self.warnings:
            logger.warning("RESULT: PASSED WITH WARNINGS")
        else:
            logger.info("RESULT: PASSED - Database is clean")

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()


def main():
    """Run database validation."""
    parser = argparse.ArgumentParser(description="Validate portfolio database integrity")
    parser.add_argument(
        "--db-path", default="portfolio.db", help="Path to SQLite database (default: portfolio.db)"
    )
    args = parser.parse_args()

    try:
        validator = DatabaseValidator(args.db_path)
        issues, warnings = validator.run_all_checks()
        validator.print_report()
        validator.close()

        # Exit code: 1 if critical issues, 0 otherwise
        sys.exit(1 if issues > 0 else 0)

    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
