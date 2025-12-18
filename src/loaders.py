"""
Data loaders for different trading platforms.

Each loader reads platform-specific CSV formats and normalises
transactions into the canonical Transaction model.
"""
import logging
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from src.models import Platform, TaxWrapper, Transaction, TransactionType
from src.utils import (
    find_csv_files,
    normalise_fund_name,
    parse_date,
    parse_money,
    parse_price,
    parse_quantity,
)


logger = logging.getLogger(__name__)


class BaseLoader(ABC):
    """Abstract base class for platform-specific data loaders."""

    platform: Platform

    def __init__(self, data_directory: Path):
        """
        Initialise the loader.

        Args:
            data_directory: Path to directory containing CSV files.
        """
        self.data_directory = Path(data_directory)
        logger.info(f"Initialised {self.__class__.__name__} with {self.data_directory}")

    @abstractmethod
    def load(self) -> list[Transaction]:
        """
        Load all transactions from CSV files.

        Returns:
            List of Transaction objects.
        """
        pass

    @abstractmethod
    def _parse_row(self, row: pd.Series) -> Optional[Transaction]:
        """
        Parse a single row into a Transaction.

        Args:
            row: A pandas Series representing one CSV row.

        Returns:
            Transaction object or None if row should be skipped.
        """
        pass

    @abstractmethod
    def _determine_tax_wrapper(self, row: pd.Series) -> TaxWrapper:
        """
        Determine the tax wrapper from a row.

        Args:
            row: A pandas Series representing one CSV row.

        Returns:
            TaxWrapper enum value.
        """
        pass

    @abstractmethod
    def _determine_transaction_type(self, row: pd.Series) -> TransactionType:
        """
        Determine the transaction type from a row.

        Args:
            row: A pandas Series representing one CSV row.

        Returns:
            TransactionType enum value.
        """
        pass


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


def load_all_transactions(
    fidelity_dir: Optional[Path] = None,
    ii_dir: Optional[Path] = None,
) -> list[Transaction]:
    """
    Convenience function to load transactions from all platforms.

    Args:
        fidelity_dir: Path to Fidelity data directory.
        ii_dir: Path to Interactive Investor data directory.

    Returns:
        Combined list of all transactions, sorted by date.
    """
    all_transactions: list[Transaction] = []

    if fidelity_dir and fidelity_dir.exists():
        loader = FidelityLoader(fidelity_dir)
        all_transactions.extend(loader.load())

    if ii_dir and ii_dir.exists():
        loader = InteractiveInvestorLoader(ii_dir)
        all_transactions.extend(loader.load())

    # Sort by date
    all_transactions.sort(key=lambda t: t.date)

    logger.info(f"Loaded {len(all_transactions)} total transactions")
    return all_transactions


if __name__ == "__main__":
    # Example usage
    import logging
    from pathlib import Path

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # Example with Fidelity data
    fidelity_dir = Path("/mnt/user-data/uploads")

    if fidelity_dir.exists():
        loader = FidelityLoader(
            data_directory=fidelity_dir,
            file_pattern="TransactionHistory*.csv",
        )
        transactions = loader.load()

        print(f"\nLoaded {len(transactions)} Fidelity transactions")

        # Show first few
        print("\nFirst 5 transactions:")
        for tx in transactions[:5]:
            print(f"  {tx.date} | {tx.tax_wrapper} | {tx.transaction_type} | "
                  f"{tx.fund_name[:30]} | £{tx.value:,.2f}")

        # Filter example: Blue Whale in ISA
        blue_whale_isa = [
            tx for tx in transactions
            if "blue whale" in tx.fund_name.lower()
            and tx.tax_wrapper == TaxWrapper.ISA
        ]

        print(f"\nBlue Whale ISA transactions: {len(blue_whale_isa)}")
        for tx in blue_whale_isa:
            print(f"  {tx.date} | {tx.transaction_type} | "
                  f"{tx.units:,.2f} units @ £{tx.price_per_unit:.4f} | £{tx.value:,.2f}")
