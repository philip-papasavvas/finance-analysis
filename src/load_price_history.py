"""
Script to load price history data from CSV files into the database.
"""
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import TransactionDatabase
from src.price_history_loader import PriceHistoryLoader

# Get the database path from the root directory
DB_PATH = Path(__file__).parent.parent / "portfolio.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)

logger = logging.getLogger(__name__)


def load_price_history():
    """Load price history data from CSV files into the database."""
    logger.info("=" * 80)
    logger.info("LOADING PRICE HISTORY DATA")
    logger.info("=" * 80)

    # Load price history from CSV files
    loader = PriceHistoryLoader()
    records = loader.load_price_data()

    if not records:
        logger.error("No price history records loaded!")
        return

    # Insert into database
    db = TransactionDatabase(str(DB_PATH))

    inserted, duplicates = db.insert_price_histories(records)

    logger.info("=" * 80)
    logger.info(f"✓ Inserted {inserted} price history records")
    logger.info(f"✓ Skipped {duplicates} duplicates")
    logger.info("=" * 80)

    # Show summary
    logger.info("\nPrice History Summary:")
    ticker_info = db.get_ticker_info()
    for info in ticker_info:
        logger.info(
            f"  {info['ticker']:<20} {info['fund_name']:<50} "
            f"{info['first_date']} to {info['last_date']} ({info['record_count']} records)"
        )

    db.close()


if __name__ == "__main__":
    load_price_history()
