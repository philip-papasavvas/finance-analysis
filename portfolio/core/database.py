"""
Database module for storing and querying portfolio transactions.

Uses SQLite to persist transaction data.
"""
import logging
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

from portfolio.core.models import Transaction

logger = logging.getLogger(__name__)


class TransactionDatabase:
    """SQLite database for portfolio transactions."""

    def __init__(self, db_path: str | Path = "portfolio.db"):
        """
        Initialize the database connection.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self.create_tables()
        logger.info(f"Connected to database: {self.db_path}")

    def create_tables(self) -> None:
        """
        Create the database tables if they don't exist.

        Tables created:
        - transactions: Core buy/sell transaction data from trading platforms
        - price_history: Daily closing prices for tickers (from yfinance)
        - fund_ticker_mapping: Maps fund names to ticker symbols for price lookup

        Note: mapping_status table is created separately by migrate_ticker_mappings.py
        See DATABASE_SCHEMA.md for full documentation.
        """
        cursor = self.conn.cursor()

        # transactions: Core transaction data from all trading platforms
        # Contains buy/sell records, fund names, values, and mapped names
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                tax_wrapper TEXT NOT NULL,
                date TEXT NOT NULL,
                fund_name TEXT NOT NULL,
                transaction_type TEXT NOT NULL,
                units REAL NOT NULL,
                price_per_unit REAL NOT NULL,
                value REAL NOT NULL,
                currency TEXT DEFAULT 'GBP',
                sedol TEXT,
                reference TEXT,
                raw_description TEXT,
                excluded INTEGER DEFAULT 0,
                mapped_fund_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, date, fund_name, transaction_type, value, reference)
            )
        """
        )

        # price_history: Daily closing prices for all tracked tickers
        # Data sourced from yfinance; used for charts and valuations
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                fund_name TEXT NOT NULL,
                close_price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, ticker)
            )
        """
        )

        # Create indexes for common queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_date ON transactions(date)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_fund_name ON transactions(fund_name)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_platform ON transactions(platform)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tax_wrapper ON transactions(tax_wrapper)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_price_date ON price_history(date)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_price_ticker ON price_history(ticker)
        """
        )

        # fund_ticker_mapping: Links fund names to ticker symbols
        # Enables joining transactions to price_history for valuations
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fund_ticker_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fund_name TEXT NOT NULL,
                ticker TEXT NOT NULL,
                sedol TEXT,
                isin TEXT,
                mapped_fund_name TEXT,
                is_auto_mapped INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(fund_name, ticker)
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_fund_ticker_fund_name
            ON fund_ticker_mapping(fund_name)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_fund_ticker_ticker
            ON fund_ticker_mapping(ticker)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_fund_ticker_sedol
            ON fund_ticker_mapping(sedol)
        """
        )

        self.conn.commit()
        logger.info("Database tables created/verified")

    def insert_transaction(self, transaction: Transaction) -> bool:
        """
        Insert a single transaction into the database.

        Args:
            transaction: Transaction object to insert.

        Returns:
            True if inserted, False if duplicate.
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO transactions (
                    platform, tax_wrapper, date, fund_name, transaction_type,
                    units, price_per_unit, value, currency, sedol, reference, raw_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    transaction.platform.name,
                    transaction.tax_wrapper.name,
                    transaction.date.isoformat(),
                    transaction.fund_name,
                    transaction.transaction_type.name,
                    transaction.units,
                    transaction.price_per_unit,
                    transaction.value,
                    transaction.currency,
                    transaction.sedol,
                    transaction.reference,
                    transaction.raw_description,
                ),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate transaction
            return False

    def insert_transactions(self, transactions: list[Transaction]) -> tuple[int, int]:
        """
        Insert multiple transactions into the database.

        Args:
            transactions: List of Transaction objects to insert.

        Returns:
            Tuple of (inserted_count, duplicate_count).
        """
        inserted = 0
        duplicates = 0

        for transaction in transactions:
            if self.insert_transaction(transaction):
                inserted += 1
            else:
                duplicates += 1

        logger.info(f"Inserted {inserted} transactions, skipped {duplicates} duplicates")
        return inserted, duplicates

    def get_all_transactions(self) -> list[dict]:
        """
        Get all transactions from the database.

        Returns:
            List of transaction dictionaries.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM transactions ORDER BY date
        """
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_transactions_by_fund(self, fund_name: str) -> list[dict]:
        """
        Get transactions for a specific fund (partial match).

        Args:
            fund_name: Fund name to search for (case-insensitive).

        Returns:
            List of matching transactions.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM transactions
            WHERE fund_name LIKE ?
            ORDER BY date
        """,
            (f"%{fund_name}%",),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_transactions_by_date_range(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """
        Get transactions within a date range.

        Args:
            start_date: Start date (inclusive).
            end_date: End date (inclusive).

        Returns:
            List of transactions.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT * FROM transactions
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        """,
            (start_date.isoformat(), end_date.isoformat()),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_summary_stats(self) -> dict:
        """
        Get summary statistics from the database.

        Returns:
            Dictionary with summary statistics.
        """
        cursor = self.conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM transactions")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT MIN(date) as first_date, MAX(date) as last_date FROM transactions")
        dates = cursor.fetchone()

        cursor.execute(
            """
            SELECT transaction_type, COUNT(*) as count
            FROM transactions
            GROUP BY transaction_type
        """
        )
        by_type = {row["transaction_type"]: row["count"] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT platform, COUNT(*) as count
            FROM transactions
            GROUP BY platform
        """
        )
        by_platform = {row["platform"]: row["count"] for row in cursor.fetchall()}

        cursor.execute(
            """
            SELECT COUNT(DISTINCT fund_name) as unique_funds
            FROM transactions
        """
        )
        unique_funds = cursor.fetchone()["unique_funds"]

        return {
            "total_transactions": total,
            "first_date": dates["first_date"],
            "last_date": dates["last_date"],
            "by_type": by_type,
            "by_platform": by_platform,
            "unique_funds": unique_funds,
        }

    def get_unique_funds(self) -> list[str]:
        """
        Get list of unique fund names.

        Returns:
            Sorted list of unique fund names.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT fund_name
            FROM transactions
            ORDER BY fund_name
        """
        )
        return [row["fund_name"] for row in cursor.fetchall()]

    def exclude_fund(self, fund_name: str) -> None:
        """
        Mark all transactions for a fund as excluded.

        Args:
            fund_name: The fund name to exclude.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE transactions SET excluded = 1 WHERE fund_name = ?
        """,
            (fund_name,),
        )
        self.conn.commit()
        logger.info(f"Excluded fund: {fund_name}")

    def set_mapped_fund_name(self, fund_name: str, mapped_name: str) -> None:
        """
        Set the mapped fund name for transactions.

        Args:
            fund_name: The original fund name.
            mapped_name: The mapped fund name.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE transactions SET mapped_fund_name = ? WHERE fund_name = ? AND mapped_fund_name IS NULL
        """,
            (mapped_name, fund_name),
        )
        self.conn.commit()
        logger.info(f"Set mapped name: {fund_name} → {mapped_name}")

    def clear_all_transactions(self) -> int:
        """
        Delete all transactions from the database.

        Returns:
            Number of deleted rows.
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM transactions")
        deleted = cursor.rowcount
        self.conn.commit()
        logger.warning(f"Deleted {deleted} transactions from database")
        return deleted

    def insert_price_history(
        self, date: str, ticker: str, fund_name: str, close_price: float
    ) -> bool:
        """
        Insert a single price history record into the database.

        Args:
            date: Date in YYYY-MM-DD format.
            ticker: Ticker symbol.
            fund_name: Fund or instrument name.
            close_price: Closing price for the day.

        Returns:
            True if inserted, False if duplicate.
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO price_history (date, ticker, fund_name, close_price)
                VALUES (?, ?, ?, ?)
            """,
                (date, ticker, fund_name, close_price),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Duplicate record
            return False

    def insert_price_histories(self, records: list[dict]) -> tuple[int, int]:
        """
        Insert multiple price history records into the database.

        Args:
            records: List of dictionaries with 'date', 'ticker', 'fund_name', 'close_price'.

        Returns:
            Tuple of (inserted_count, duplicate_count).
        """
        inserted = 0
        duplicates = 0

        for record in records:
            if self.insert_price_history(
                record["date"], record["ticker"], record["fund_name"], record["close_price"]
            ):
                inserted += 1
            else:
                duplicates += 1

        logger.info(f"Inserted {inserted} price records, skipped {duplicates} duplicates")
        return inserted, duplicates

    def get_price_history_by_ticker(self, ticker: str) -> list[dict]:
        """
        Get all price history records for a specific ticker.

        Args:
            ticker: Ticker symbol.

        Returns:
            List of price history records sorted by date.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT date, ticker, fund_name, close_price
            FROM price_history
            WHERE ticker = ?
            ORDER BY date
        """,
            (ticker,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_all_price_tickers(self) -> list[str]:
        """
        Get all unique tickers in the price history database.

        Returns:
            Sorted list of unique ticker symbols.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT ticker FROM price_history ORDER BY ticker
        """
        )
        return [row["ticker"] for row in cursor.fetchall()]

    def get_ticker_info(self) -> list[dict]:
        """
        Get information about all tickers in price history (ticker, fund_name, first_date, last_date, record_count).

        Returns:
            List of dictionaries with ticker information.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                ticker,
                fund_name,
                MIN(date) as first_date,
                MAX(date) as last_date,
                COUNT(*) as record_count
            FROM price_history
            GROUP BY ticker
            ORDER BY ticker
        """
        )
        return [dict(row) for row in cursor.fetchall()]

    def add_fund_ticker_mapping(
        self,
        fund_name: str,
        ticker: str,
        sedol: Optional[str] = None,
        isin: Optional[str] = None,
        is_auto_mapped: bool = False,
    ) -> bool:
        """
        Add a fund-to-ticker mapping.

        Args:
            fund_name: The fund name from transactions.
            ticker: The ticker symbol in price_history.
            sedol: Optional SEDOL code.
            isin: Optional ISIN code.
            is_auto_mapped: Whether this was auto-extracted or manually mapped.

        Returns:
            True if inserted, False if duplicate.
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO fund_ticker_mapping
                (fund_name, ticker, sedol, isin, is_auto_mapped)
                VALUES (?, ?, ?, ?, ?)
            """,
                (fund_name, ticker, sedol, isin, 1 if is_auto_mapped else 0),
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_ticker_for_fund(self, fund_name: str) -> Optional[str]:
        """
        Get the ticker symbol for a fund name.

        Args:
            fund_name: The fund name to look up.

        Returns:
            Ticker symbol if found, None otherwise.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT ticker FROM fund_ticker_mapping
            WHERE fund_name = ?
            LIMIT 1
        """,
            (fund_name,),
        )
        result = cursor.fetchone()
        return result["ticker"] if result else None

    def get_transactions_for_ticker(self, ticker: str) -> list[dict]:
        """
        Get buy/sell transactions for a specific ticker.

        Joins transactions → fund_ticker_mapping → price_history to get
        transaction details with the price from the transaction date.

        Args:
            ticker: The ticker symbol.

        Returns:
            List of transaction records with date, type, units, prices, and marker_y.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT
                t.date,
                t.transaction_type,
                t.units,
                t.price_per_unit,
                t.value,
                t.fund_name,
                ph.close_price as marker_y
            FROM transactions t
            INNER JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
            INNER JOIN price_history ph ON ftm.ticker = ph.ticker AND t.date = ph.date
            WHERE ftm.ticker = ?
              AND t.excluded = 0
              AND t.transaction_type IN ('BUY', 'SELL')
            ORDER BY t.date
        """,
            (ticker,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_all_fund_ticker_mappings(self) -> list[dict]:
        """
        Get all fund-to-ticker mappings.

        Returns:
            List of mapping records.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT fund_name, ticker, sedol, isin, is_auto_mapped, created_at
            FROM fund_ticker_mapping
            ORDER BY ticker, fund_name
        """
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()
        logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Example usage
    import logging
    from load_transactions import main as load_transactions

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # Load transactions from CSV
    print("Loading transactions from CSV files...")
    transactions = load_transactions()

    # Save to database
    print("\nSaving to database...")
    with TransactionDatabase("portfolio.db") as db:
        inserted, duplicates = db.insert_transactions(transactions)
        print(f"✓ Inserted {inserted} new transactions")
        print(f"✓ Skipped {duplicates} duplicates")

        # Show summary
        print("\nDatabase Summary:")
        stats = db.get_summary_stats()
        print(f"  Total transactions: {stats['total_transactions']}")
        print(f"  Date range: {stats['first_date']} to {stats['last_date']}")
        print(f"  Unique funds: {stats['unique_funds']}")
        print(f"  By platform: {stats['by_platform']}")
        print(f"  By type: {stats['by_type']}")
