"""
Database migration script to create fund_ticker_mapping table.
"""
import logging
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Get the database path from the root directory
DB_PATH = Path(__file__).parent.parent / "portfolio.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)

logger = logging.getLogger(__name__)


def create_mapping_table():
    """Create the fund_ticker_mapping table."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    logger.info("=" * 80)
    logger.info("CREATING FUND_TICKER_MAPPING TABLE")
    logger.info("=" * 80)

    try:
        cursor.execute("""
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
        """)

        logger.info("✓ Table created successfully")

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fund_ticker_fund_name
            ON fund_ticker_mapping(fund_name)
        """)
        logger.info("✓ Index on fund_name created")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fund_ticker_ticker
            ON fund_ticker_mapping(ticker)
        """)
        logger.info("✓ Index on ticker created")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fund_ticker_sedol
            ON fund_ticker_mapping(sedol)
        """)
        logger.info("✓ Index on sedol created")

        conn.commit()
        conn.close()

        logger.info("=" * 80)
        logger.info("Migration completed successfully!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Error creating table: {e}")
        conn.close()
        raise


if __name__ == "__main__":
    create_mapping_table()
