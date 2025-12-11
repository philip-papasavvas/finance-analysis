"""
Load all transactions from CSV files and display summary.
"""
import logging
from pathlib import Path

from src.loaders import FidelityLoader, InteractiveInvestorLoader
from src.reports import TransactionReport, get_unique_funds

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Load all transactions and display summary."""
    data_dir = Path("./data")

    # Load Fidelity transactions
    logger.info("Loading Fidelity transactions...")
    fidelity_loader = FidelityLoader(
        data_directory=data_dir,
        file_pattern="fidelity*.csv",
        skip_rows=6,
    )
    fidelity_transactions = fidelity_loader.load()

    # Load Interactive Investor transactions
    logger.info("Loading Interactive Investor transactions...")
    ii_loader = InteractiveInvestorLoader(
        data_directory=data_dir,
        file_pattern="ii_isa_*.csv",
        skip_rows=0,
    )
    ii_transactions = ii_loader.load()

    # Combine all transactions
    all_transactions = fidelity_transactions + ii_transactions
    all_transactions.sort(key=lambda t: t.date)

    logger.info(f"\n{'='*80}")
    logger.info(f"TRANSACTION SUMMARY")
    logger.info(f"{'='*80}")
    logger.info(f"Total Fidelity transactions: {len(fidelity_transactions)}")
    logger.info(f"Total II transactions: {len(ii_transactions)}")
    logger.info(f"Total transactions: {len(all_transactions)}")

    if all_transactions:
        logger.info(f"Date range: {all_transactions[0].date} to {all_transactions[-1].date}")

        # Get unique funds
        unique_funds = get_unique_funds(all_transactions)
        logger.info(f"\nUnique funds ({len(unique_funds)}):")
        for fund in unique_funds[:10]:  # Show first 10
            logger.info(f"  - {fund}")
        if len(unique_funds) > 10:
            logger.info(f"  ... and {len(unique_funds) - 10} more")

        # Transaction type breakdown
        buy_count = sum(1 for t in all_transactions if t.is_buy)
        sell_count = sum(1 for t in all_transactions if t.is_sell)
        logger.info(f"\nTransaction types:")
        logger.info(f"  Buy: {buy_count}")
        logger.info(f"  Sell: {sell_count}")
        logger.info(f"  Other: {len(all_transactions) - buy_count - sell_count}")

        # Show first few transactions
        logger.info(f"\nFirst 5 transactions:")
        for tx in all_transactions[:5]:
            logger.info(
                f"  {tx.date} | {tx.platform.name[:4]} | {tx.tax_wrapper.name} | "
                f"{tx.transaction_type.name} | {tx.fund_name[:40]:<40} | £{tx.value:>10,.2f}"
            )

    return all_transactions


if __name__ == "__main__":
    transactions = main()
    print(f"\n✓ Successfully loaded {len(transactions)} transactions!")