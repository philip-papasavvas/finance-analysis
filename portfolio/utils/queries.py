"""
Query examples for the transaction database.
"""
import logging
from datetime import date
from pathlib import Path

from portfolio.core.database import TransactionDatabase

# Get the database path from the root directory
DB_PATH = Path(__file__).parent.parent / "portfolio.db"

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(message)s",
)


def main():
    """Run example queries on the database."""
    with TransactionDatabase(str(DB_PATH)) as db:
        print("=" * 80)
        print("PORTFOLIO DATABASE QUERIES")
        print("=" * 80)

        # 1. Summary statistics
        print("\n1. Database Summary:")
        stats = db.get_summary_stats()
        print(f"   Total transactions: {stats['total_transactions']}")
        print(f"   Date range: {stats['first_date']} to {stats['last_date']}")
        print(f"   Unique funds: {stats['unique_funds']}")
        print("   By platform:")
        for platform, count in stats["by_platform"].items():
            print(f"     - {platform}: {count}")
        print("   By transaction type:")
        for tx_type, count in stats["by_type"].items():
            print(f"     - {tx_type}: {count}")

        # 2. Get all unique funds
        print("\n2. All Unique Funds:")
        funds = db.get_unique_funds()
        for i, fund in enumerate(funds[:10], 1):
            print(f"   {i:2d}. {fund}")
        if len(funds) > 10:
            print(f"   ... and {len(funds) - 10} more")

        # 3. Search for specific funds
        print("\n3. Transactions for 'Blue Whale' fund:")
        blue_whale_txs = db.get_transactions_by_fund("Blue Whale")
        print(f"   Found {len(blue_whale_txs)} transactions")
        for tx in blue_whale_txs[:5]:
            print(
                f"   {tx['date']} | {tx['transaction_type']:4s} | "
                f"{tx['units']:>8.2f} units @ £{tx['price_per_unit']:>6.2f} | "
                f"£{tx['value']:>10,.2f}"
            )
        if len(blue_whale_txs) > 5:
            print(f"   ... and {len(blue_whale_txs) - 5} more")

        # 4. Transactions in a date range
        print("\n4. Transactions in 2024:")
        txs_2024 = db.get_transactions_by_date_range(
            date(2024, 1, 1),
            date(2024, 12, 31),
        )
        print(f"   Found {len(txs_2024)} transactions in 2024")

        # Calculate total bought and sold in 2024
        total_bought = sum(tx["value"] for tx in txs_2024 if tx["transaction_type"] == "BUY")
        total_sold = sum(tx["value"] for tx in txs_2024 if tx["transaction_type"] == "SELL")
        print(f"   Total bought: £{total_bought:,.2f}")
        print(f"   Total sold: £{total_sold:,.2f}")

        # 5. Search for technology funds
        print("\n5. Technology-related funds:")
        tech_funds = [
            f for f in funds if any(term in f.lower() for term in ["tech", "technology", "polar"])
        ]
        print(f"   Found {len(tech_funds)} technology funds:")
        for fund in tech_funds:
            txs = db.get_transactions_by_fund(fund)
            total_value = sum(tx["value"] for tx in txs if tx["transaction_type"] == "BUY")
            print(f"   - {fund[:60]:<60} ({len(txs)} txs, £{total_value:,.2f})")

        # 6. Most recent transactions
        print("\n6. 10 Most Recent Transactions:")
        all_txs = db.get_all_transactions()
        for tx in all_txs[-10:]:
            print(
                f"   {tx['date']} | {tx['platform'][:4]:>4s} | "
                f"{tx['transaction_type']:4s} | {tx['fund_name'][:40]:<40} | "
                f"£{tx['value']:>10,.2f}"
            )

        print("\n" + "=" * 80)
        print("✓ All queries completed successfully!")
        print("=" * 80)


if __name__ == "__main__":
    main()
