"""
Migration script to:
1. Create mapping_status table
2. Update 'Fidelity Funds' transactions to mapped name
3. Add fund ticker mappings
4. Populate mapping_status table with date ranges
"""
import json
import logging
from pathlib import Path

from src.database import TransactionDatabase

# Get the database path from the root directory
DB_PATH = Path(__file__).parent.parent / "portfolio.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)

logger = logging.getLogger(__name__)


def create_mapping_status_table(db: TransactionDatabase) -> None:
    """Create the mapping_status table if it doesn't exist."""
    cursor = db.conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mapping_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            fund_name TEXT,
            earliest_date TEXT,
            latest_date TEXT,
            transaction_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_mapping_status_ticker
        ON mapping_status(ticker)
    """)

    db.conn.commit()
    logger.info("✓ mapping_status table created/verified")


def update_fidelity_funds_mapping(db: TransactionDatabase) -> int:
    """Update 'Fidelity Funds' transactions to the mapped name."""
    cursor = db.conn.cursor()

    # Check how many Fidelity Funds records exist
    cursor.execute("""
        SELECT COUNT(*) as count FROM transactions
        WHERE fund_name = 'Fidelity Funds' AND excluded = 0
    """)
    count = cursor.fetchone()["count"]

    if count > 0:
        mapped_name = "Fidelity Funds - Global Technology Fund W-ACC-GBP"
        cursor.execute("""
            UPDATE transactions
            SET mapped_fund_name = ?
            WHERE fund_name = 'Fidelity Funds' AND excluded = 0 AND mapped_fund_name IS NULL
        """, (mapped_name,))
        db.conn.commit()
        logger.info(f"✓ Updated {count} 'Fidelity Funds' transactions to '{mapped_name}'")
        return count
    else:
        logger.info("✓ No 'Fidelity Funds' transactions found to update")
        return 0


def add_fund_ticker_mappings(db: TransactionDatabase) -> int:
    """Add fund-to-ticker mappings for specified funds."""
    mappings = [
        ("ISHARES IV PLC, MSCI USA SRI UCITS ETF USD ACC (SUUS)", "SUUS.L", None, None),
        ("SCOTTISH MORTGAGE INV TRUST, ORD GBP0.05 (SMT)", "SMT.L", None, None),
        ("Fidelity Funds - Global Technology Fund W-ACC-GBP", "LU1033663649", "BJVDZ16", "LU1033663649"),
    ]

    added_count = 0
    for fund_name, ticker, sedol, isin in mappings:
        cursor = db.conn.cursor()

        # Check if fund exists in transactions
        cursor.execute("""
            SELECT COUNT(*) as count FROM transactions
            WHERE (fund_name = ? OR mapped_fund_name = ?)
        """, (fund_name, fund_name))
        exists = cursor.fetchone()["count"] > 0

        if exists:
            if db.add_fund_ticker_mapping(fund_name, ticker, sedol, isin):
                logger.info(f"✓ Added mapping: {fund_name} → {ticker}")
                added_count += 1
            else:
                logger.info(f"⊘ Mapping already exists: {fund_name} → {ticker}")
        else:
            logger.info(f"⊘ Fund not found in transactions: {fund_name}")

    return added_count


def populate_mapping_status(db: TransactionDatabase) -> int:
    """Populate mapping_status table with date ranges for all tickers."""
    cursor = db.conn.cursor()

    # Get all unique fund-ticker mappings
    cursor.execute("""
        SELECT DISTINCT ticker, fund_name FROM fund_ticker_mapping
        ORDER BY ticker
    """)
    mappings = cursor.fetchall()

    updated_count = 0

    for mapping in mappings:
        ticker = mapping["ticker"]
        fund_name = mapping["fund_name"]

        # Get date range for this fund from transactions
        cursor.execute("""
            SELECT MIN(date) as earliest_date, MAX(date) as latest_date, COUNT(*) as count
            FROM transactions
            WHERE (fund_name = ? OR mapped_fund_name = ?) AND excluded = 0
        """, (fund_name, fund_name))
        result = cursor.fetchone()

        if result["count"] > 0:
            earliest = result["earliest_date"]
            latest = result["latest_date"]

            # Insert or update mapping_status
            cursor.execute("""
                INSERT INTO mapping_status (ticker, fund_name, earliest_date, latest_date, transaction_count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(ticker) DO UPDATE SET
                    earliest_date = excluded.earliest_date,
                    latest_date = excluded.latest_date,
                    transaction_count = excluded.transaction_count,
                    updated_at = CURRENT_TIMESTAMP
            """, (ticker, fund_name, earliest, latest, result["count"]))
            db.conn.commit()

            logger.info(f"✓ {ticker}: {earliest} → {latest} ({result['count']} transactions)")
            updated_count += 1

    return updated_count


def apply_fund_name_mappings(db: TransactionDatabase) -> int:
    """Apply fund name mappings from JSON to update mapped_fund_name."""
    mapping_file = Path(__file__).parent.parent / "mappings" / "fund_rename_mapping.json"

    if not mapping_file.exists():
        logger.error(f"Mapping file not found: {mapping_file}")
        return 0

    with open(mapping_file, "r") as f:
        mappings = json.load(f)

    updated_count = 0

    for original_name, mapped_name in mappings.items():
        cursor = db.conn.cursor()

        # Check if this fund exists in the database
        cursor.execute("""
            SELECT COUNT(*) as count FROM transactions
            WHERE fund_name = ? AND excluded = 0
        """, (original_name,))
        count = cursor.fetchone()["count"]

        if count > 0:
            # Update the mapped_fund_name column
            cursor.execute("""
                UPDATE transactions
                SET mapped_fund_name = ?
                WHERE fund_name = ? AND excluded = 0 AND mapped_fund_name IS NULL
            """, (mapped_name, original_name))
            db.conn.commit()
            updated_count += count

    return updated_count


def main():
    """Run all migrations."""
    logger.info("=" * 80)
    logger.info("MIGRATION: TICKER MAPPINGS AND MAPPING STATUS")
    logger.info("=" * 80)

    db = TransactionDatabase(str(DB_PATH))

    try:
        # Step 1: Create mapping_status table
        logger.info("\n[1/5] Creating mapping_status table...")
        create_mapping_status_table(db)

        # Step 2: Update Fidelity Funds mappings
        logger.info("\n[2/5] Updating 'Fidelity Funds' records...")
        fidelity_count = update_fidelity_funds_mapping(db)

        # Step 3: Apply all fund name mappings from JSON
        logger.info("\n[3/5] Applying fund name mappings from JSON...")
        mapping_count = apply_fund_name_mappings(db)
        logger.info(f"✓ Applied mappings to {mapping_count} transactions")

        # Step 4: Add fund-to-ticker mappings
        logger.info("\n[4/5] Adding fund-to-ticker mappings...")
        ticker_count = add_fund_ticker_mappings(db)

        # Step 5: Populate mapping_status table
        logger.info("\n[5/5] Populating mapping_status table...")
        status_count = populate_mapping_status(db)

        logger.info(f"\n{'='*80}")
        logger.info("✓ MIGRATION COMPLETED SUCCESSFULLY")
        logger.info(f"  - Fidelity Funds updated: {fidelity_count}")
        logger.info(f"  - Fund name mappings applied: {mapping_count}")
        logger.info(f"  - Fund-to-ticker mappings added: {ticker_count}")
        logger.info(f"  - Mapping status entries: {status_count}")
        logger.info(f"{'='*80}")

    finally:
        db.close()


if __name__ == "__main__":
    main()