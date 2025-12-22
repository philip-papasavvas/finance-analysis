"""
Database migration script to add new columns.
"""
import logging
import sqlite3
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)

logger = logging.getLogger(__name__)


def migrate():
    """Add excluded and mapped_fund_name columns if they don't exist."""
    # Get the database path from the root directory
    db_path = Path(__file__).parent.parent / "portfolio.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    logger.info("=" * 80)
    logger.info("MIGRATING DATABASE")
    logger.info("=" * 80)

    # Check and add excluded column
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN excluded INTEGER DEFAULT 0")
        logger.info("✓ Added 'excluded' column")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("  'excluded' column already exists")
        else:
            raise

    # Check and add mapped_fund_name column
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN mapped_fund_name TEXT")
        logger.info("✓ Added 'mapped_fund_name' column")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            logger.info("  'mapped_fund_name' column already exists")
        else:
            raise

    logger.info("=" * 80)
    logger.info("Migration complete!")
    logger.info("=" * 80)

    conn.close()


if __name__ == "__main__":
    migrate()
