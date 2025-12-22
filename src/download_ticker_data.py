"""
Script to download price data for tickers and add to database.
"""
import logging
from datetime import datetime
from pathlib import Path

import yfinance as yf

from src.database import TransactionDatabase

# Get the database path from the root directory
DB_PATH = Path(__file__).parent.parent / "portfolio.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)

logger = logging.getLogger(__name__)


def download_ticker_data(ticker: str, fund_name: str) -> list[dict]:
    """
    Download historical price data for a ticker using yfinance.

    Args:
        ticker: Ticker symbol (e.g., SUUS.L, SMT.L, LU1033663649)
        fund_name: Fund name for reference

    Returns:
        List of price records with date, ticker, fund_name, close_price
    """
    logger.info(f"Downloading data for {ticker} ({fund_name})...")

    try:
        # Download data - start from 2019 to get historical data
        data = yf.download(ticker, start="2019-01-01", progress=False, auto_adjust=False)

        # Check if data is empty
        if len(data) == 0:
            logger.warning(f"⚠ No data found for {ticker}")
            return []

        records = []
        for date, row in data.iterrows():
            try:
                close_price = float(row["Close"])
                if close_price > 0:  # Skip zero prices
                    records.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "ticker": ticker,
                        "fund_name": fund_name,
                        "close_price": close_price
                    })
            except (ValueError, TypeError, KeyError):
                continue

        logger.info(f"✓ Downloaded {len(records)} records for {ticker}")
        return records

    except Exception as e:
        logger.error(f"✗ Error downloading {ticker}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def add_price_data_to_db(db: TransactionDatabase, records: list[dict]) -> tuple[int, int]:
    """Add price records to database and return counts."""
    if not records:
        return 0, 0

    inserted, duplicates = db.insert_price_histories(records)
    return inserted, duplicates


def update_mapping_status_for_ticker(db: TransactionDatabase, ticker: str) -> None:
    """Update mapping_status table for a specific ticker."""
    cursor = db.conn.cursor()

    # Get the fund name for this ticker
    cursor.execute("""
        SELECT fund_name FROM fund_ticker_mapping
        WHERE ticker = ?
        LIMIT 1
    """, (ticker,))
    result = cursor.fetchone()

    if result is None:
        logger.warning(f"⚠ No fund mapping found for {ticker}")
        return

    fund_name = result["fund_name"]

    # Get date range from transactions
    cursor.execute("""
        SELECT MIN(date) as earliest_date, MAX(date) as latest_date, COUNT(*) as count
        FROM transactions
        WHERE (fund_name = ? OR mapped_fund_name = ?) AND excluded = 0
    """, (fund_name, fund_name))
    trans_result = cursor.fetchone()

    # Get date range from price history
    cursor.execute("""
        SELECT MIN(date) as earliest_price_date, MAX(date) as latest_price_date, COUNT(*) as price_count
        FROM price_history
        WHERE ticker = ?
    """, (ticker,))
    price_result = cursor.fetchone()

    # Update mapping_status
    cursor.execute("""
        INSERT INTO mapping_status (ticker, fund_name, earliest_date, latest_date, transaction_count)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
            earliest_date = excluded.earliest_date,
            latest_date = excluded.latest_date,
            transaction_count = excluded.transaction_count,
            updated_at = CURRENT_TIMESTAMP
    """, (
        ticker,
        fund_name,
        trans_result["earliest_date"],
        trans_result["latest_date"],
        trans_result["count"]
    ))
    db.conn.commit()

    if price_result["price_count"] > 0:
        logger.info(
            f"✓ {ticker} price data: {price_result['earliest_price_date']} → "
            f"{price_result['latest_price_date']} ({price_result['price_count']} records)"
        )


def main():
    """Run the download and database update process."""
    logger.info("=" * 80)
    logger.info("DOWNLOADING TICKER PRICE DATA")
    logger.info("=" * 80)

    db = TransactionDatabase(str(DB_PATH))

    try:
        # Step 1: Download price data for all tickers
        logger.info("\n[1/3] Downloading price data...")
        tickers_to_download = [
            ("SUUS.L", "ISHARES IV PLC, MSCI USA SRI UCITS ETF USD ACC (SUUS)"),
            ("SMT.L", "SCOTTISH MORTGAGE INV TRUST, ORD GBP0.05 (SMT)"),
            ("LU1033663649", "Fidelity Funds - Global Technology Fund W-ACC-GBP"),
        ]

        all_records = []
        for ticker, fund_name in tickers_to_download:
            records = download_ticker_data(ticker, fund_name)
            all_records.extend(records)

        # Step 2: Add price data to database
        logger.info("\n[2/3] Adding price data to database...")
        total_inserted = 0
        total_duplicates = 0

        for ticker, _ in tickers_to_download:
            ticker_records = [r for r in all_records if r["ticker"] == ticker]
            inserted, duplicates = add_price_data_to_db(db, ticker_records)
            total_inserted += inserted
            total_duplicates += duplicates

        # Step 3: Update mapping_status for each ticker
        logger.info("\n[3/3] Updating mapping_status table...")
        for ticker, _ in tickers_to_download:
            update_mapping_status_for_ticker(db, ticker)

        logger.info(f"\n{'='*80}")
        logger.info("✓ PRICE DATA DOWNLOAD COMPLETED")
        logger.info(f"  - Total records inserted: {total_inserted}")
        logger.info(f"  - Total duplicates skipped: {total_duplicates}")
        logger.info(f"{'='*80}")

    finally:
        db.close()


if __name__ == "__main__":
    main()