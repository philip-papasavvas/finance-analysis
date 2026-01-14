"""
Script to exclude specific funds from the portfolio.
"""
import logging
from pathlib import Path

from portfolio.core.database import TransactionDatabase

# Get the database path from the root directory
DB_PATH = Path(__file__).parent.parent / "portfolio.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)

logger = logging.getLogger(__name__)

# Funds to exclude (these are duplicates or old positions to ignore)
FUNDS_TO_EXCLUDE = [
    "1200 FUNH LLPSTD VAN FD  Bal    1.76 S Date 08/11/21",
    "1341.13 FUNH LLPSTD VAN FD  Bal    1.80 S Date 15/11/21",
    "1826.07 FUNH LLPSTD VAN FD  Del    1.63 S Date 18/06/21",
    "715.06 FUNH LLPSTD VAN FD  Del    1.66 S Date 01/07/21",
    "13 MULI UNITETF  Del  299.03 S Date 18/01/24",
    "16 MULI UNITETF  Del  291.65 S Date 14/12/23",
    "6 MULI UNITETF  Del  308.92 S Date 05/02/24",
    "8 MULI UNITETF  Del  313.25 S Date 01/02/24",
    "First Sentier",
    "Link Solutions",
]


def exclude_funds():
    """Exclude specified funds from the portfolio."""
    db = TransactionDatabase(str(DB_PATH))

    logger.info("=" * 80)
    logger.info("EXCLUDING FUNDS FROM PORTFOLIO")
    logger.info("=" * 80)

    for fund_name in FUNDS_TO_EXCLUDE:
        # Check if fund exists
        cursor = db.conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as count FROM transactions WHERE fund_name = ?
        """,
            (fund_name,),
        )
        count = cursor.fetchone()["count"]

        if count > 0:
            db.exclude_fund(fund_name)
            logger.info(f"✓ Excluded: {fund_name} ({count} transactions)")
        else:
            logger.warning(f"⚠ Fund not found: {fund_name}")

    logger.info("=" * 80)
    logger.info("Done! Funds have been excluded from the portfolio.")
    logger.info("=" * 80)

    db.close()


if __name__ == "__main__":
    exclude_funds()
