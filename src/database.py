"""
Database module for storing and querying portfolio transactions.

Uses SQLite to persist transaction data.
"""
import logging
import sqlite3
from datetime import date
from pathlib import Path
from typing import Optional

from src.models import Platform, TaxWrapper, Transaction, TransactionType

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
        """Create the transactions and fund_name_mapping tables if they don't exist."""
        cursor = self.conn.cursor()

        cursor.execute("""
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, date, fund_name, transaction_type, value, reference)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fund_name_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL UNIQUE,
                standardized_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_date ON transactions(date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fund_name ON transactions(fund_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_platform ON transactions(platform)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tax_wrapper ON transactions(tax_wrapper)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_original_name ON fund_name_mapping(original_name)
        """)

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
            cursor.execute("""
                INSERT INTO transactions (
                    platform, tax_wrapper, date, fund_name, transaction_type,
                    units, price_per_unit, value, currency, sedol, reference, raw_description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
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
            ))
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
        cursor.execute("""
            SELECT * FROM transactions ORDER BY date
        """)
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
        cursor.execute("""
            SELECT * FROM transactions
            WHERE fund_name LIKE ?
            ORDER BY date
        """, (f"%{fund_name}%",))
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
        cursor.execute("""
            SELECT * FROM transactions
            WHERE date BETWEEN ? AND ?
            ORDER BY date
        """, (start_date.isoformat(), end_date.isoformat()))
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

        cursor.execute("""
            SELECT transaction_type, COUNT(*) as count
            FROM transactions
            GROUP BY transaction_type
        """)
        by_type = {row["transaction_type"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT platform, COUNT(*) as count
            FROM transactions
            GROUP BY platform
        """)
        by_platform = {row["platform"]: row["count"] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT COUNT(DISTINCT fund_name) as unique_funds
            FROM transactions
        """)
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
        cursor.execute("""
            SELECT DISTINCT fund_name
            FROM transactions
            ORDER BY fund_name
        """)
        return [row["fund_name"] for row in cursor.fetchall()]

    def add_fund_mapping(self, original_name: str, standardized_name: str) -> bool:
        """
        Add a fund name mapping to the database.

        Args:
            original_name: The original fund name.
            standardized_name: The standardized fund name.

        Returns:
            True if inserted, False if mapping already exists.
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO fund_name_mapping (original_name, standardized_name)
                VALUES (?, ?)
            """, (original_name, standardized_name))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Mapping already exists
            return False

    def get_standardized_name(self, original_name: str) -> str:
        """
        Get the standardized name for a fund.

        Args:
            original_name: The original fund name.

        Returns:
            The standardized name if mapping exists, otherwise the original name.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT standardized_name FROM fund_name_mapping
            WHERE original_name = ?
        """, (original_name,))
        result = cursor.fetchone()

        if result:
            return result["standardized_name"]
        return original_name

    def get_all_fund_mappings(self) -> dict[str, str]:
        """
        Get all fund name mappings.

        Returns:
            Dictionary mapping original names to standardized names.
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT original_name, standardized_name FROM fund_name_mapping
            ORDER BY original_name
        """)
        return {row["original_name"]: row["standardized_name"] for row in cursor.fetchall()}

    def clear_fund_mappings(self) -> int:
        """
        Delete all fund name mappings from the database.

        Returns:
            Number of deleted mappings.
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM fund_name_mapping")
        deleted = cursor.rowcount
        self.conn.commit()
        logger.warning(f"Deleted {deleted} fund name mappings from database")
        return deleted

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