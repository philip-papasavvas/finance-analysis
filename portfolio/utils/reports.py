"""
Report generation for portfolio analyzer.

Generates transaction tables and summary reports from loaded data.
"""
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

from portfolio.core.database import TransactionDatabase
from portfolio.core.models import Platform, TaxWrapper, Transaction, TransactionType


logger = logging.getLogger(__name__)


@dataclass
class TransactionFilter:
    """Filter criteria for transaction queries."""

    fund_name: Optional[str] = None
    platform: Optional[Platform] = None
    tax_wrapper: Optional[TaxWrapper] = None
    transaction_type: Optional[TransactionType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    def matches(self, transaction: Transaction) -> bool:
        """Check if a transaction matches all filter criteria."""
        if self.fund_name:
            if self.fund_name.lower() not in transaction.fund_name.lower():
                return False

        if self.platform and transaction.platform != self.platform:
            return False

        if self.tax_wrapper and transaction.tax_wrapper != self.tax_wrapper:
            return False

        if self.transaction_type and transaction.transaction_type != self.transaction_type:
            return False

        if self.start_date and transaction.date < self.start_date:
            return False

        if self.end_date and transaction.date > self.end_date:
            return False

        return True


class TransactionReport:
    """Generate transaction reports and tables."""

    def __init__(self, transactions: list[Transaction], db_path: str = "portfolio.db"):
        """
        Initialise with a list of transactions.

        Args:
            transactions: List of Transaction objects.
            db_path: Path to the SQLite database for fund name mappings.
        """
        self.transactions = transactions
        self.db_path = db_path
        self.fund_mappings: dict[str, str] = {}
        self._load_fund_mappings()
        logger.info(f"TransactionReport initialised with {len(transactions)} transactions")

    def _load_fund_mappings(self) -> None:
        """Load fund name mappings from the database."""
        try:
            db = TransactionDatabase(self.db_path)
            self.fund_mappings = db.get_all_fund_mappings()
            db.close()
            if self.fund_mappings:
                logger.info(f"Loaded {len(self.fund_mappings)} fund name mappings")
        except Exception as e:
            logger.warning(f"Could not load fund mappings: {e}")
            self.fund_mappings = {}

    def get_standardized_name(self, original_name: str) -> str:
        """
        Get the standardized name for a fund.

        Args:
            original_name: The original fund name.

        Returns:
            The standardized name if mapping exists, otherwise the original name.
        """
        return self.fund_mappings.get(original_name, original_name)

    def filter(self, criteria: TransactionFilter) -> list[Transaction]:
        """
        Filter transactions by criteria.

        Args:
            criteria: TransactionFilter with filter parameters.

        Returns:
            Filtered list of transactions.
        """
        filtered = [tx for tx in self.transactions if criteria.matches(tx)]
        logger.debug(f"Filtered to {len(filtered)} transactions")
        return filtered

    def to_dataframe(
        self,
        transactions: Optional[list[Transaction]] = None,
    ) -> pd.DataFrame:
        """
        Convert transactions to a pandas DataFrame.

        Args:
            transactions: List of transactions to convert.
                         Uses all transactions if not specified.

        Returns:
            DataFrame with transaction data.
        """
        if transactions is None:
            transactions = self.transactions

        if not transactions:
            return pd.DataFrame()

        records = [tx.to_dict() for tx in transactions]
        df = pd.DataFrame(records)

        # Order columns
        column_order = [
            "Tax Wrapper",
            "Platform",
            "Date",
            "Fund Name",
            "Buy/Sell",
            "Units",
            "Price (£)",
            "Value (£)",
        ]

        # Only include columns that exist
        columns = [c for c in column_order if c in df.columns]
        return df[columns]

    def generate_fund_report(
        self,
        fund_name: str,
        platform: Optional[Platform] = None,
        tax_wrapper: Optional[TaxWrapper] = None,
    ) -> pd.DataFrame:
        """
        Generate a transaction report for a specific fund.

        Args:
            fund_name: Fund name to filter by (partial match).
            platform: Optional platform filter.
            tax_wrapper: Optional tax wrapper filter.

        Returns:
            DataFrame with filtered transactions.
        """
        criteria = TransactionFilter(
            fund_name=fund_name,
            platform=platform,
            tax_wrapper=tax_wrapper,
        )

        filtered = self.filter(criteria)
        return self.to_dataframe(filtered)

    def generate_summary(
        self,
        transactions: Optional[list[Transaction]] = None,
    ) -> dict:
        """
        Generate summary statistics for transactions.

        Args:
            transactions: List of transactions to summarise.
                         Uses all transactions if not specified.

        Returns:
            Dictionary with summary statistics.
        """
        if transactions is None:
            transactions = self.transactions

        if not transactions:
            return {}

        buys = [tx for tx in transactions if tx.is_buy]
        sells = [tx for tx in transactions if tx.is_sell]

        total_bought = sum(tx.value for tx in buys)
        total_sold = sum(tx.value for tx in sells)
        units_bought = sum(tx.units for tx in buys)
        units_sold = sum(tx.units for tx in sells)

        return {
            "total_transactions": len(transactions),
            "buy_transactions": len(buys),
            "sell_transactions": len(sells),
            "total_bought": total_bought,
            "total_sold": total_sold,
            "units_bought": units_bought,
            "units_sold": units_sold,
            "units_remaining": units_bought - units_sold,
            "first_date": min(tx.date for tx in transactions),
            "last_date": max(tx.date for tx in transactions),
        }

    def to_markdown(
        self,
        transactions: Optional[list[Transaction]] = None,
    ) -> str:
        """
        Generate a markdown table from transactions.

        Args:
            transactions: List of transactions to include.
                         Uses all transactions if not specified.

        Returns:
            Markdown formatted table string.
        """
        df = self.to_dataframe(transactions)

        if df.empty:
            return "No transactions found."

        return df.to_markdown(index=False)

    def to_dataframe_with_standardized(
        self,
        transactions: Optional[list[Transaction]] = None,
    ) -> pd.DataFrame:
        """
        Convert transactions to a DataFrame with standardized fund names.

        Args:
            transactions: List of transactions to convert.
                         Uses all transactions if not specified.

        Returns:
            DataFrame with transaction data, showing standardized fund names.
        """
        df = self.to_dataframe(transactions)

        if df.empty or "Fund Name" not in df.columns:
            return df

        # Create a column with standardized names
        df["Standardized Fund Name"] = df["Fund Name"].apply(self.get_standardized_name)

        # Reorder columns to show standardized name next to original
        column_order = [
            "Tax Wrapper",
            "Platform",
            "Date",
            "Fund Name",
            "Standardized Fund Name",
            "Buy/Sell",
            "Units",
            "Price (£)",
            "Value (£)",
        ]

        columns = [c for c in column_order if c in df.columns]
        return df[columns]

    def to_csv(
        self,
        output_path: Path,
        transactions: Optional[list[Transaction]] = None,
    ) -> None:
        """
        Export transactions to a CSV file.

        Args:
            output_path: Path to output CSV file.
            transactions: List of transactions to export.
                         Uses all transactions if not specified.
        """
        df = self.to_dataframe(transactions)
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(df)} transactions to {output_path}")


def get_unique_funds(transactions: list[Transaction]) -> list[str]:
    """
    Get a list of unique fund names from transactions.

    Args:
        transactions: List of transactions.

    Returns:
        Sorted list of unique fund names.
    """
    return sorted(set(tx.fund_name for tx in transactions))


def get_fund_transactions(
    transactions: list[Transaction],
    fund_name: str,
    platform: Optional[Platform] = None,
    tax_wrapper: Optional[TaxWrapper] = None,
) -> list[Transaction]:
    """
    Get transactions for a specific fund.

    Convenience function for common filtering operation.

    Args:
        transactions: List of all transactions.
        fund_name: Fund name to filter by (partial match, case-insensitive).
        platform: Optional platform filter.
        tax_wrapper: Optional tax wrapper filter.

    Returns:
        Filtered list of transactions.
    """
    result = []
    fund_lower = fund_name.lower()

    for tx in transactions:
        if fund_lower not in tx.fund_name.lower():
            continue

        if platform and tx.platform != platform:
            continue

        if tax_wrapper and tx.tax_wrapper != tax_wrapper:
            continue

        result.append(tx)

    return result


if __name__ == "__main__":
    # Example usage
    import logging
    from pathlib import Path

    from loaders import FidelityLoader
    from models import Platform, TaxWrapper

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # Load Fidelity data
    fidelity_dir = Path("/mnt/user-data/uploads")
    loader = FidelityLoader(fidelity_dir)
    transactions = loader.load()

    # Create report generator
    report = TransactionReport(transactions)

    # Get Blue Whale transactions in Fidelity ISA
    blue_whale_df = report.generate_fund_report(
        fund_name="Blue Whale",
        platform=Platform.FIDELITY,
        tax_wrapper=TaxWrapper.ISA,
    )

    print("\nBlue Whale Growth - Fidelity ISA Transactions:")
    print("=" * 80)
    print(blue_whale_df.to_string(index=False))

    # Get summary
    criteria = TransactionFilter(
        fund_name="Blue Whale",
        platform=Platform.FIDELITY,
        tax_wrapper=TaxWrapper.ISA,
    )
    filtered = report.filter(criteria)
    summary = report.generate_summary(filtered)

    print("\nSummary:")
    print(f"  Total Bought: £{summary['total_bought']:,.2f} ({summary['units_bought']:,.2f} units)")
    print(f"  Total Sold: £{summary['total_sold']:,.2f} ({summary['units_sold']:,.2f} units)")
    print(f"  Units Remaining: {summary['units_remaining']:,.2f}")

    # List all unique funds
    print("\nUnique funds in portfolio:")
    for fund in get_unique_funds(transactions):
        print(f"  - {fund}")
