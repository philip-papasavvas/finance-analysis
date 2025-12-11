"""
Standardize fund names in the database to consolidate duplicates.
"""
import logging
import re
import sqlite3

from src.database import TransactionDatabase

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)

logger = logging.getLogger(__name__)


def create_fund_name_mapping() -> dict[str, str]:
    """
    Create a mapping of fund names to their standardized versions.

    Returns:
        Dictionary mapping original names to standardized names.
    """
    mapping = {
        # Blue Whale variants → Blue Whale Growth R Acc
        "WS Blue Whale Growth": "Blue Whale Growth R Acc",
        "WS Blue Whale Growth Fund R Acc": "Blue Whale Growth R Acc",

        # Scottish Mortgage variants → Scottish Mortgage
        "SCOTTISH MORTGAGE INV TRUST, ORD GBP0.05 (SMT)": "Scottish Mortgage",

        # Polar Capital variants → Polar Capital Technology
        "Polar Capital Global Technology I GBP": "Polar Capital Technology",

        # Fidelity variants → Fidelity Global Tech
        "Fidelity Funds - Global Technology Fund W-ACC-GBP": "Fidelity Global Tech",
        "Fidelity Investment": "Fidelity Global Tech",
    }

    return mapping


def extract_ticker_from_name(fund_name: str) -> str:
    """
    Extract ticker symbol from fund names with format "NAME (TICK)".

    Args:
        fund_name: Fund name potentially containing a ticker in parentheses.

    Returns:
        Ticker symbol if found, otherwise original name.
    """
    # Match 3-4 letter ticker in parentheses at the end
    ticker_pattern = re.compile(r'\(([A-Z]{3,4})\)$')
    match = ticker_pattern.search(fund_name)

    if match:
        return match.group(1)

    return fund_name


def standardize_fund_names(db_path: str = "portfolio.db", dry_run: bool = True) -> None:
    """
    Standardize fund names in the database.

    Args:
        db_path: Path to the SQLite database.
        dry_run: If True, show what would change without modifying the database.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all unique fund names
    cursor.execute('SELECT DISTINCT fund_name FROM transactions ORDER BY fund_name')
    all_funds = [row[0] for row in cursor.fetchall()]

    # Create mapping
    mapping = create_fund_name_mapping()

    # Add ticker-based mappings for funds with parentheses
    for fund in all_funds:
        if re.search(r'\([A-Z]{3,4}\)$', fund):
            standardized = extract_ticker_from_name(fund)
            if standardized != fund:
                mapping[fund] = standardized

    logger.info("="*80)
    logger.info(f"FUND NAME STANDARDIZATION {'(DRY RUN)' if dry_run else ''}")
    logger.info("="*80)

    changes_made = 0

    for original, standardized in sorted(mapping.items()):
        # Check if this fund exists in the database
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE fund_name = ?', (original,))
        count = cursor.fetchone()[0]

        if count > 0:
            logger.info(f"\n{original}")
            logger.info(f"  → {standardized}")
            logger.info(f"  ({count} transactions)")

            if not dry_run:
                cursor.execute(
                    'UPDATE transactions SET fund_name = ? WHERE fund_name = ?',
                    (standardized, original)
                )
                changes_made += count

    if not dry_run:
        conn.commit()
        logger.info(f"\n{'='*80}")
        logger.info(f"✓ Updated {changes_made} transactions")

        # Show new unique fund count
        cursor.execute('SELECT COUNT(DISTINCT fund_name) FROM transactions')
        new_count = cursor.fetchone()[0]
        logger.info(f"✓ Unique funds after standardization: {new_count}")
    else:
        logger.info(f"\n{'='*80}")
        logger.info("This was a DRY RUN - no changes were made")
        logger.info("Run with dry_run=False to apply changes")

    conn.close()


def populate_fund_mappings(db_path: str = "portfolio.db") -> None:
    """
    Populate the fund_name_mapping table in the database.

    Creates mappings for all funds based on the standardization rules.

    Args:
        db_path: Path to the SQLite database.
    """
    db = TransactionDatabase(db_path)

    # Get all unique fund names from transactions
    all_funds = db.get_unique_funds()

    # Create mapping rules
    mapping = create_fund_name_mapping()

    # Add ticker-based mappings for funds with parentheses
    for fund in all_funds:
        if re.search(r'\([A-Z]{3,4}\)$', fund):
            standardized = extract_ticker_from_name(fund)
            if standardized != fund and fund not in mapping:
                mapping[fund] = standardized

    logger.info("="*80)
    logger.info("POPULATING FUND NAME MAPPING TABLE")
    logger.info("="*80)

    added = 0
    skipped = 0

    for original, standardized in sorted(mapping.items()):
        if db.add_fund_mapping(original, standardized):
            logger.info(f"✓ Added mapping: {original} → {standardized}")
            added += 1
        else:
            skipped += 1

    logger.info(f"\n{'='*80}")
    logger.info(f"✓ Added {added} mappings to the database")
    logger.info(f"✓ Skipped {skipped} existing mappings")
    logger.info(f"{'='*80}")

    db.close()


def show_standardized_summary(db_path: str = "portfolio.db") -> None:
    """Show summary of funds after standardization."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("\n" + "="*80)
    logger.info("FUND SUMMARY AFTER STANDARDIZATION")
    logger.info("="*80)

    cursor.execute('''
        SELECT fund_name, COUNT(*) as tx_count
        FROM transactions
        GROUP BY fund_name
        ORDER BY tx_count DESC
        LIMIT 15
    ''')

    logger.info("\nTop 15 funds by transaction count:")
    for fund, count in cursor.fetchall():
        logger.info(f"  {count:3d} | {fund}")

    conn.close()


if __name__ == "__main__":
    # First, show what would change (dry run)
    print("\n" + "="*80)
    print("STEP 1: DRY RUN - Preview changes")
    print("="*80)
    standardize_fund_names(dry_run=True)

    # Ask for confirmation
    print("\n" + "="*80)
    response = input("\nApply these changes? (yes/no): ").strip().lower()

    if response == "yes":
        print("\n" + "="*80)
        print("STEP 2: Applying changes...")
        print("="*80)
        standardize_fund_names(dry_run=False)

        # Populate the mapping table
        print("\n" + "="*80)
        print("STEP 3: Populating fund name mapping table...")
        print("="*80)
        populate_fund_mappings()

        # Show summary
        show_standardized_summary()
    else:
        print("\nNo changes were made.")