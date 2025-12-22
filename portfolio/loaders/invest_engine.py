"""
InvestEngine platform transaction loader.
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


class InvestEngineLoader(BaseLoader):
    """Loader for InvestEngine transaction history CSV files."""

    platform = Platform.INVEST_ENGINE

    def __init__(
        self,
        data_directory: Path,
        file_pattern: str = "invest_engine_*.csv",
        skip_rows: int = 1,
    ):
        """
        Initialise the InvestEngine loader.

        Args:
            data_directory: Path to directory containing InvestEngine CSV files.
            file_pattern: Glob pattern to match CSV files.
            skip_rows: Number of header rows to skip in CSV files.
        """
        super().__init__(data_directory)
        self.file_pattern = file_pattern
        self.skip_rows = skip_rows
        self.current_filename = None  # Track filename for tax wrapper detection

    def load(self) -> list[Transaction]:
        """Load all InvestEngine transactions from CSV files."""
        csv_files = find_csv_files(self.data_directory, self.file_pattern)

        if not csv_files:
            logger.warning(f"No InvestEngine CSV files found in {self.data_directory}")
            return []

        all_transactions: list[Transaction] = []

        for csv_file in csv_files:
            logger.info(f"Loading InvestEngine file: {csv_file.name}")
            # Set current filename for tax wrapper detection
            self.current_filename = csv_file.name.lower()
            try:
                df = pd.read_csv(
                    csv_file,
                    skiprows=self.skip_rows,
                    encoding="utf-8-sig",
                )
                df.columns = df.columns.str.strip()

                for _, row in df.iterrows():
                    transaction = self._parse_row(row)
                    if transaction:
                        all_transactions.append(transaction)

            except Exception as e:
                logger.error(f"Error loading {csv_file}: {e}")

        # Sort by date
        all_transactions.sort(key=lambda t: t.date)
        logger.info(f"Loaded {len(all_transactions)} InvestEngine transactions")

        return all_transactions

    def _parse_row(self, row: pd.Series) -> Optional[Transaction]:
        """Parse an InvestEngine CSV row into a Transaction."""
        # Parse quantity
        units = parse_quantity(row.get("Quantity", 0))
        if units == 0:
            return None

        # Parse date
        tx_date = parse_date(row.get("Trade Date/Time", ""))
        if not tx_date:
            return None

        # Parse values
        value = abs(parse_money(row.get("Total Trade Value", 0)))
        price = parse_price(row.get("Share Price", 0))

        if value == 0:
            return None

        # Extract ISIN from "Security / ISIN" column (format: "Fund Name / ISIN XXX")
        security_info = str(row.get("Security / ISIN", "")).strip()
        isin = self._extract_isin(security_info)

        # Extract fund name
        fund_name = self._extract_fund_name(security_info)

        return Transaction(
            platform=self.platform,
            tax_wrapper=self._determine_tax_wrapper(row),
            date=tx_date,
            fund_name=fund_name,
            transaction_type=self._determine_transaction_type(row),
            units=units,
            price_per_unit=price,
            value=value,
            sedol=isin if isin else None,  # Store ISIN as sedol
            raw_description=security_info,
        )

    def _extract_isin(self, security_info: str) -> Optional[str]:
        """Extract ISIN from security info string."""
        # Format: "Fund Name / ISIN XXX"
        if " / ISIN " in security_info:
            return security_info.split(" / ISIN ")[-1].strip()
        return None

    def _extract_fund_name(self, security_info: str) -> str:
        """Extract fund name from security info string."""
        # Format: "Fund Name / ISIN XXX"
        if " / ISIN " in security_info:
            return security_info.split(" / ISIN ")[0].strip()
        return security_info.strip()

    def _determine_tax_wrapper(self, row: pd.Series) -> TaxWrapper:
        """Determine tax wrapper from filename context."""
        if not self.current_filename:
            return TaxWrapper.OTHER

        # Check filename for tax wrapper indicators
        if "isa" in self.current_filename:
            return TaxWrapper.ISA
        elif "gia" in self.current_filename:
            return TaxWrapper.GIA
        elif "sipp" in self.current_filename:
            return TaxWrapper.SIPP
        else:
            return TaxWrapper.OTHER

    def _determine_transaction_type(self, row: pd.Series) -> TransactionType:
        """Determine transaction type from Transaction Type column."""
        tx_type = str(row.get("Transaction Type", "")).strip().lower()

        if "buy" in tx_type:
            return TransactionType.BUY
        elif "sell" in tx_type:
            return TransactionType.SELL
        else:
            return TransactionType.OTHER
