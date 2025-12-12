"""
Script to populate fund_ticker_mapping table with automatic and manual mappings.
"""
import json
import logging
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import TransactionDatabase

DB_PATH = Path(__file__).parent.parent / "portfolio.db"
MAPPING_FILE = Path(__file__).parent.parent / "mappings" / "fund_ticker_mapping.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)

logger = logging.getLogger(__name__)


def extract_ticker_from_fund_name(fund_name: str) -> Optional[str]:
    """
    Extract ticker from fund name if in parentheses.

    Examples:
        "INVESCO PHYSICAL GOLD (SGLP)" -> "SGLP"
        "ISHARES MSCI USA SRI (SUUS)" -> "SUUS"
        "SCOTTISH MORTGAGE INV TRUST, ORD GBP0.05 (SMT)" -> "SMT"
    """
    match = re.search(r"\(([A-Z]{3,5})\)", fund_name)
    if match:
        return match.group(1)
    return None


def get_price_history_tickers() -> set:
    """Get all tickers from price_history table."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ticker FROM price_history")
    tickers = {row[0] for row in cursor.fetchall()}
    conn.close()
    return tickers


def match_ticker_with_price_history(extracted_ticker: str, available_tickers: set) -> Optional[str]:
    """
    Try to match extracted ticker with available price history tickers.

    Tries variations like: VUAG -> VUAG.L, VUAG.DE, etc.
    """
    # Direct match
    if extracted_ticker in available_tickers:
        return extracted_ticker

    # Try with common suffixes
    for suffix in [".L", ".DE", ".US", ""]:
        candidate = f"{extracted_ticker}{suffix}"
        if candidate in available_tickers:
            return candidate

    return None


def populate_auto_mappings():
    """Automatically extract tickers from fund names and create mappings."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get all unique fund names with transactions
    cursor.execute("""
        SELECT DISTINCT fund_name, sedol
        FROM transactions
        WHERE excluded = 0
    """)
    funds = cursor.fetchall()

    # Get available price history tickers
    price_tickers = get_price_history_tickers()

    logger.info("=" * 80)
    logger.info("AUTO-EXTRACTING TICKER MAPPINGS")
    logger.info("=" * 80)
    logger.info(f"Scanning {len(funds)} unique fund names...")
    logger.info(f"Available price tickers: {sorted(price_tickers)}")
    logger.info("")

    auto_mapped = 0
    no_ticker_found = 0
    no_price_data = 0

    for fund in funds:
        fund_name = fund["fund_name"]
        sedol = fund["sedol"]

        # Try to extract ticker
        extracted = extract_ticker_from_fund_name(fund_name)

        if not extracted:
            no_ticker_found += 1
            continue

        # Try to match with price history
        matched_ticker = match_ticker_with_price_history(extracted, price_tickers)

        if not matched_ticker:
            logger.debug(f"  ⚠ Extracted '{extracted}' but no price data: {fund_name}")
            no_price_data += 1
            continue

        # Insert mapping using the database method
        db = TransactionDatabase(str(DB_PATH))
        if db.add_fund_ticker_mapping(fund_name, matched_ticker, sedol, None, True):
            logger.info(f"✓ {fund_name}")
            logger.info(f"  → {matched_ticker}")
            auto_mapped += 1
        db.close()

    logger.info("")
    logger.info(f"Auto-mapped: {auto_mapped}")
    logger.info(f"No ticker pattern: {no_ticker_found}")
    logger.info(f"No price data: {no_price_data}")
    logger.info("=" * 80)

    conn.close()

    return auto_mapped, no_ticker_found, no_price_data


def populate_manual_mappings():
    """Load manual mappings from JSON file."""
    if not MAPPING_FILE.exists():
        logger.warning(f"Manual mapping file not found: {MAPPING_FILE}")
        logger.info("Skipping manual mappings...")
        return 0

    with open(MAPPING_FILE, "r") as f:
        manual_mappings = json.load(f)

    logger.info("=" * 80)
    logger.info("LOADING MANUAL TICKER MAPPINGS")
    logger.info("=" * 80)

    manual_mapped = 0

    for fund_name, ticker in manual_mappings.items():
        db = TransactionDatabase(str(DB_PATH))
        if db.add_fund_ticker_mapping(fund_name, ticker, None, None, False):
            logger.info(f"✓ {fund_name}")
            logger.info(f"  → {ticker}")
            manual_mapped += 1
        db.close()

    logger.info("")
    logger.info(f"Manual mappings added: {manual_mapped}")
    logger.info("=" * 80)

    return manual_mapped


def show_summary():
    """Show summary of mappings."""
    db = TransactionDatabase(str(DB_PATH))
    mappings = db.get_all_fund_ticker_mappings()
    db.close()

    logger.info("")
    logger.info("=" * 80)
    logger.info("MAPPING SUMMARY BY TICKER")
    logger.info("=" * 80)

    # Group by ticker
    ticker_groups = {}
    for mapping in mappings:
        ticker = mapping["ticker"]
        if ticker not in ticker_groups:
            ticker_groups[ticker] = []
        ticker_groups[ticker].append(mapping)

    for ticker in sorted(ticker_groups.keys()):
        group = ticker_groups[ticker]
        logger.info(f"  {ticker:<20} ({len(group)} fund names)")
        for mapping in group:
            auto_label = " [auto]" if mapping["is_auto_mapped"] else " [manual]"
            logger.info(f"    - {mapping['fund_name']}{auto_label}")

    logger.info("")
    logger.info(f"Total mappings: {len(mappings)}")
    logger.info(f"Unique tickers: {len(ticker_groups)}")
    logger.info("=" * 80)


if __name__ == "__main__":
    try:
        populate_auto_mappings()
        populate_manual_mappings()
        show_summary()
    except Exception as e:
        logger.error(f"Error during population: {e}")
        raise
