"""
Interactive Investor platform transaction loader.
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


class InteractiveInvestorLoader(BaseLoader):
    """Loader for Interactive Investor transaction history CSV files."""

    platform = Platform.INTERACTIVE_INVESTOR

    # Fund name mappings from II's abbreviated descriptions
    FUND_MAPPINGS = {
        "ALLZ TECH": "Allianz Technology Trust",
        "LIONT SPEC SIT": "Liontrust Special Situations",
        "ISHS PHYSETCMD": "iShares Physical Gold",
        "FDSMITH": "Fundsmith Equity",
        "LEG & GEN US": "L&G US Index",
        "FIL INV": "Fidelity Investment",
        "AXA INV": "AXA Framlington",
        "VAN LIFE": "Vanguard LifeStrategy",
        "FIRT SENT": "First Sentier",
        "LEGT TRUS": "Legal & General",
        "LINK SOLU": "Link Solutions",
        "VANGUARD": "Vanguard",
        "GAM STAR": "GAM Star",
        "SCOH MORT": "Scottish Mortgage",
        "SCOTTISH MORTGAGE": "Scottish Mortgage",
        "POLAR CAP TECH": "Polar Capital Technology",
        "ISHARES GBL EN": "iShares Global Clean Energy",
        "LINDSELL TRAIN": "Lindsell Train Global Equity",
        "COIE GLOB": "Coinbase Global",
        "SPOY TECH": "Spotify",
        "M&G SECU": "M&G Securities",
        "FIDY FUNDSTD": "Fidelity Funds",
        "WS BLUE": "WS Blue Whale Growth",
        "BLUESTD": "Blue Whale Growth",
        "WS BLUESTD": "WS Blue Whale Growth",
        "BAIE GIFF": "Baillie Gifford",
    }

    def __init__(
        self,
        data_directory: Path,
        file_pattern: str = "ii_isa_*.csv",
        skip_rows: int = 0,
    ):
        """
        Initialise the Interactive Investor loader.

        Args:
            data_directory: Path to directory containing II CSV files.
            file_pattern: Glob pattern to match CSV files.
            skip_rows: Number of header rows to skip in CSV files.
        """
        super().__init__(data_directory)
        self.file_pattern = file_pattern
        self.skip_rows = skip_rows

    def load(self) -> list[Transaction]:
        """Load all Interactive Investor transactions from CSV files."""
        csv_files = find_csv_files(self.data_directory, self.file_pattern)

        if not csv_files:
            logger.warning(f"No II CSV files found in {self.data_directory}")
            return []

        all_transactions: list[Transaction] = []

        for csv_file in csv_files:
            logger.info(f"Loading II file: {csv_file.name}")
            try:
                df = pd.read_csv(csv_file, encoding="utf-8-sig")
                # Clean column names (remove BOM characters)
                df.columns = df.columns.str.replace("\ufeff", "").str.strip()

                for _, row in df.iterrows():
                    transaction = self._parse_row(row)
                    if transaction:
                        all_transactions.append(transaction)

            except Exception as e:
                logger.error(f"Error loading {csv_file}: {e}")

        # Sort by date
        all_transactions.sort(key=lambda t: t.date)
        logger.info(f"Loaded {len(all_transactions)} II transactions")

        return all_transactions

    def _parse_row(self, row: pd.Series) -> Optional[Transaction]:
        """Parse an Interactive Investor CSV row into a Transaction."""
        # Parse quantity - if no quantity, this isn't a trade
        units = parse_quantity(row.get("Quantity", "n/a"))
        if units == 0:
            return None

        # Check for valid sedol (trades have sedol)
        sedol = str(row.get("Sedol", "n/a")).strip()
        if sedol == "n/a" or not sedol:
            return None

        # Parse date
        tx_date = parse_date(row.get("Date", ""))
        if not tx_date:
            return None

        # Determine transaction type from debit/credit
        debit = parse_money(row.get("Debit", 0))
        credit = parse_money(row.get("Credit", 0))

        if debit > 0:
            tx_type = TransactionType.BUY
            value = debit
        elif credit > 0:
            tx_type = TransactionType.SELL
            value = credit
        else:
            return None

        # Parse price
        price = parse_price(row.get("Price", 0))

        # Extract fund name from description
        description = str(row.get("Description", ""))
        fund_name = self._extract_fund_name(description)

        return Transaction(
            platform=self.platform,
            tax_wrapper=self._determine_tax_wrapper(row),
            date=tx_date,
            fund_name=fund_name,
            transaction_type=tx_type,
            units=units,
            price_per_unit=price,
            value=value,
            sedol=sedol if sedol != "n/a" else None,
            raw_description=description,
        )

    def _extract_fund_name(self, description: str) -> str:
        """Extract and normalise fund name from II description."""
        upper_desc = description.upper()

        for pattern, name in self.FUND_MAPPINGS.items():
            if pattern in upper_desc:
                return name

        # Fallback: return cleaned description
        return description.strip()

    def _determine_tax_wrapper(self, row: pd.Series) -> TaxWrapper:
        """
        Determine tax wrapper.

        Note: II CSVs are typically per-account, so this is usually ISA.
        Could be extended to parse from filename or additional columns.
        """
        # Default to ISA for now - could be made configurable
        return TaxWrapper.ISA

    def _determine_transaction_type(self, row: pd.Series) -> TransactionType:
        """Determine transaction type from debit/credit columns."""
        debit = parse_money(row.get("Debit", 0))

        if debit > 0:
            return TransactionType.BUY
        else:
            return TransactionType.SELL
