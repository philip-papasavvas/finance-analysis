"""
Fidelity platform transaction loader.
"""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from portfolio.core.models import Platform, TaxWrapper, Transaction, TransactionType
from portfolio.utils.helpers import (
    find_csv_files,
    parse_date,
    parse_money,
    parse_price,
    parse_quantity,
)
from .base import BaseLoader


logger = logging.getLogger(__name__)


class FidelityLoader(BaseLoader):
    """Loader for Fidelity transaction history CSV files."""

    platform = Platform.FIDELITY

    BUY_TYPES = {"Buy", "Buy For Switch", "Transfer In"}
    SELL_TYPES = {"Sell", "Sell For Switch"}

    def __init__(
        self,
        data_directory: Path,
        file_pattern: str = "TransactionHistory*.csv",
        skip_rows: int = 6,
    ):
        """
        Initialise the Fidelity loader.

        Args:
            data_directory: Path to directory containing Fidelity CSV files.
            file_pattern: Glob pattern to match CSV files.
            skip_rows: Number of header rows to skip in CSV files.
        """
        super().__init__(data_directory)
        self.file_pattern = file_pattern
        self.skip_rows = skip_rows

    def load(self) -> list[Transaction]:
        """Load all Fidelity transactions from CSV files."""
        csv_files = find_csv_files(self.data_directory, self.file_pattern)

        if not csv_files:
            logger.warning(f"No Fidelity CSV files found in {self.data_directory}")
            return []

        all_transactions: list[Transaction] = []

        for csv_file in csv_files:
            logger.info(f"Loading Fidelity file: {csv_file.name}")
            try:
                df = pd.read_csv(
                    csv_file,
                    skiprows=self.skip_rows,
                    encoding="utf-8-sig",
                )
                df.columns = df.columns.str.strip()

                # Filter for completed transactions
                if "Status" in df.columns:
                    df = df[df["Status"] == "Completed"]

                for _, row in df.iterrows():
                    transaction = self._parse_row(row)
                    if transaction:
                        all_transactions.append(transaction)

            except Exception as e:
                logger.error(f"Error loading {csv_file}: {e}")

        # Sort by date
        all_transactions.sort(key=lambda t: t.date)
        logger.info(f"Loaded {len(all_transactions)} Fidelity transactions")

        return all_transactions

    def _parse_row(self, row: pd.Series) -> Optional[Transaction]:
        """Parse a Fidelity CSV row into a Transaction."""
        tx_type = self._determine_transaction_type(row)

        # Only process buy/sell transactions
        if tx_type not in (TransactionType.BUY, TransactionType.SELL):
            return None

        # Parse date
        tx_date = parse_date(row.get("Order date", ""))
        if not tx_date:
            return None

        # Parse values
        units = parse_quantity(row.get("Quantity", 0))
        price = parse_price(row.get("Price per unit", 0))
        value = abs(parse_money(row.get("Amount", 0)))

        if units == 0 or value == 0:
            return None

        return Transaction(
            platform=self.platform,
            tax_wrapper=self._determine_tax_wrapper(row),
            date=tx_date,
            fund_name=str(row.get("Investments", "")).strip(),
            transaction_type=tx_type,
            units=units,
            price_per_unit=price,
            value=value,
            sedol=str(row.get("Sedol", "")).strip() or None,
            reference=str(row.get("Reference number", "")).strip() or None,
            raw_description=str(row.get("Transaction type", "")).strip() or None,
        )

    def _determine_tax_wrapper(self, row: pd.Series) -> TaxWrapper:
        """Determine tax wrapper from Fidelity's Product Wrapper column."""
        wrapper = str(row.get("Product Wrapper", "")).upper()

        if "SIPP" in wrapper:
            return TaxWrapper.SIPP
        elif "ISA" in wrapper:
            return TaxWrapper.ISA
        else:
            return TaxWrapper.OTHER

    def _determine_transaction_type(self, row: pd.Series) -> TransactionType:
        """Determine transaction type from Fidelity's Transaction type column."""
        tx_type = str(row.get("Transaction type", "")).strip()

        if tx_type in self.BUY_TYPES:
            return TransactionType.BUY
        elif tx_type in self.SELL_TYPES:
            return TransactionType.SELL
        else:
            return TransactionType.OTHER
