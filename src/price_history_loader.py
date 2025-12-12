"""
Loader for price history data from Yahoo Finance CSV files.

Reads CSV files with daily closing prices for financial instruments
and stores them in the database for visualization on charts.
"""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class PriceHistoryLoader:
    """Loader for Yahoo Finance price history CSV files."""

    def __init__(self, data_directory: Path = None):
        """
        Initialize the price history loader.

        Args:
            data_directory: Path to directory containing price history CSV files.
                           Defaults to the data directory in project root.
        """
        if data_directory is None:
            data_directory = Path(__file__).parent.parent / "data"

        self.data_directory = Path(data_directory)
        logger.info(f"Initialized PriceHistoryLoader with {self.data_directory}")

    def load_price_data(self, filename: str = "portfolio_funds_*.csv") -> list[dict]:
        """
        Load price history data from CSV files.

        Args:
            filename: Glob pattern to match CSV files.

        Returns:
            List of price history records with Date, Ticker, Fund Name, and Close price.
        """
        csv_files = list(self.data_directory.glob(filename))

        if not csv_files:
            logger.warning(f"No price history CSV files found matching {filename}")
            return []

        all_records = []

        for csv_file in csv_files:
            logger.info(f"Loading price history from: {csv_file.name}")
            try:
                df = pd.read_csv(csv_file)

                # Validate required columns
                required_columns = ['Date', 'Ticker', 'Fund Name', 'Close']
                if not all(col in df.columns for col in required_columns):
                    logger.warning(f"Missing required columns in {csv_file.name}")
                    continue

                # Convert to list of dictionaries
                for _, row in df.iterrows():
                    record = {
                        'date': str(row['Date']),
                        'ticker': str(row['Ticker']),
                        'fund_name': str(row['Fund Name']),
                        'close_price': float(row['Close']),
                    }
                    all_records.append(record)

            except Exception as e:
                logger.error(f"Error loading {csv_file.name}: {e}")

        logger.info(f"Loaded {len(all_records)} price history records")
        return all_records

    def get_unique_instruments(self, records: list[dict]) -> dict:
        """
        Extract unique instruments from price history records.

        Args:
            records: List of price history records.

        Returns:
            Dictionary mapping ticker to fund name.
        """
        instruments = {}
        for record in records:
            ticker = record['ticker']
            fund_name = record['fund_name']
            if ticker not in instruments:
                instruments[ticker] = fund_name

        return instruments
