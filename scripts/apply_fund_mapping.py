"""
Script to apply fund rename mappings from JSON to the database.
"""
import json
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


def apply_fund_mappings():
    """Load fund mappings from JSON and apply them to the database."""
    # Load the mapping file
    mapping_file = Path(__file__).parent.parent / "mappings" / "fund_rename_mapping.json"

    if not mapping_file.exists():
        logger.error(f"Mapping file not found: {mapping_file}")
        return

    with open(mapping_file, "r") as f:
        mappings = json.load(f)

    logger.info("=" * 80)
    logger.info("APPLYING FUND NAME MAPPINGS FROM JSON")
    logger.info("=" * 80)

    db = TransactionDatabase(str(DB_PATH))

    updated_count = 0
    not_found_count = 0

    for original_name, mapped_name in mappings.items():
        # Check if this fund exists in the database
        cursor = db.conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*) as count FROM transactions
            WHERE fund_name = ? AND excluded = 0
        """,
            (original_name,),
        )
        count = cursor.fetchone()["count"]

        if count > 0:
            # Update the mapped_fund_name column
            cursor.execute(
                """
                UPDATE transactions
                SET mapped_fund_name = ?
                WHERE fund_name = ? AND excluded = 0 AND mapped_fund_name IS NULL
            """,
                (mapped_name, original_name),
            )
            db.conn.commit()

            logger.info(f"✓ {original_name}")
            logger.info(f"  → {mapped_name} ({count} transactions)")
            updated_count += count
        else:
            not_found_count += 1

    logger.info(f"\n{'='*80}")
    logger.info(f"✓ Updated {updated_count} transactions with new fund names")
    logger.info(f"✓ {not_found_count} funds not found in database (may be excluded)")
    logger.info(f"{'='*80}")

    db.close()


if __name__ == "__main__":
    apply_fund_mappings()
