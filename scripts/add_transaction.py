#!/usr/bin/env python3
"""
Interactive Transaction Entry Script

Allows manual entry of individual transactions with validation and confirmation.
Prioritizes VIP funds for easy selection.
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from portfolio.core.database import TransactionDatabase  # noqa: E402


class TransactionEntry:
    """Interactive transaction entry with validation."""

    def __init__(self, db_path: str = "portfolio.db"):
        self.db_path = db_path
        self.db = TransactionDatabase(db_path)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """Close database connections."""
        self.db.close()
        self.conn.close()

    def get_vip_funds(self) -> List[Dict]:
        """Get all VIP funds with their mapped names."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT
                ftm.ticker,
                ftm.fund_name,
                COALESCE(
                    (SELECT COALESCE(mapped_fund_name, fund_name)
                     FROM transactions
                     WHERE fund_name = ftm.fund_name
                     LIMIT 1),
                    ftm.fund_name
                ) as display_name
            FROM fund_ticker_mapping ftm
            WHERE ftm.vip = 1
            ORDER BY display_name
        """
        )

        funds = []
        for row in cursor.fetchall():
            funds.append(
                {
                    "ticker": row["ticker"],
                    "fund_name": row["fund_name"],
                    "display_name": row["display_name"],
                }
            )
        return funds

    def get_all_funds(self) -> List[Dict]:
        """Get all unique fund names from transactions."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT
                fund_name,
                COALESCE(mapped_fund_name, fund_name) as display_name
            FROM transactions
            ORDER BY display_name
        """
        )

        funds = []
        for row in cursor.fetchall():
            funds.append({"fund_name": row["fund_name"], "display_name": row["display_name"]})
        return funds

    def select_fund(self) -> str:
        """Interactive fund selection with VIP priority."""
        print("\n" + "=" * 80)
        print("FUND SELECTION")
        print("=" * 80)

        vip_funds = self.get_vip_funds()

        if vip_funds:
            print("\nVIP Funds (⭐ Priority Holdings):")
            print("-" * 80)
            for idx, fund in enumerate(vip_funds, 1):
                print(f"  {idx:2d}. {fund['display_name']}")
                if fund["display_name"] != fund["fund_name"]:
                    print(f"      └─ Original: {fund['fund_name']}")

            print("\n  0. Enter custom fund name")
            print()

            while True:
                try:
                    choice = input("Select fund number (or 0 for custom): ").strip()

                    if choice == "0":
                        # Custom fund name entry
                        all_funds = self.get_all_funds()
                        print("\nAll known funds:")
                        for idx, fund in enumerate(all_funds[:20], 1):  # Show first 20
                            print(f"  {idx:2d}. {fund['display_name']}")
                        if len(all_funds) > 20:
                            print(f"  ... and {len(all_funds) - 20} more")

                        custom_name = input("\nEnter fund name: ").strip()
                        if custom_name:
                            return custom_name
                        else:
                            print("⚠ Fund name cannot be empty. Please try again.")
                            continue

                    idx = int(choice)
                    if 1 <= idx <= len(vip_funds):
                        selected = vip_funds[idx - 1]
                        print(f"✓ Selected: {selected['display_name']}")
                        return selected["fund_name"]
                    else:
                        print(f"⚠ Please enter a number between 0 and {len(vip_funds)}")

                except ValueError:
                    print("⚠ Please enter a valid number")
        else:
            # No VIP funds, fall back to custom entry
            print("No VIP funds found. Please enter fund name manually.")
            return input("Fund name: ").strip()

    def get_date(self) -> str:
        """Get and validate transaction date."""
        print("\n" + "=" * 80)
        print("TRANSACTION DATE")
        print("=" * 80)

        while True:
            date_str = input("\nEnter date (YYYY-MM-DD) or press Enter for today: ").strip()

            if not date_str:
                date_str = datetime.now().strftime("%Y-%m-%d")
                print(f"✓ Using today's date: {date_str}")
                return date_str

            try:
                # Validate date format
                datetime.strptime(date_str, "%Y-%m-%d")
                return date_str
            except ValueError:
                print("⚠ Invalid date format. Please use YYYY-MM-DD (e.g., 2025-12-24)")

    def get_platform(self) -> str:
        """Get platform selection."""
        print("\n" + "=" * 80)
        print("PLATFORM")
        print("=" * 80)

        platforms = ["Interactive Investor", "Fidelity", "InvestEngine", "DODL", "Other"]

        print("\nAvailable platforms:")
        for idx, platform in enumerate(platforms, 1):
            print(f"  {idx}. {platform}")

        while True:
            try:
                choice = input("\nSelect platform number: ").strip()
                idx = int(choice)
                if 1 <= idx <= len(platforms):
                    if platforms[idx - 1] == "Other":
                        custom = input("Enter platform name: ").strip()
                        return custom if custom else platforms[idx - 1]
                    return platforms[idx - 1]
                else:
                    print(f"⚠ Please enter a number between 1 and {len(platforms)}")
            except ValueError:
                print("⚠ Please enter a valid number")

    def get_tax_wrapper(self) -> str:
        """Get tax wrapper selection."""
        print("\n" + "=" * 80)
        print("TAX WRAPPER")
        print("=" * 80)

        wrappers = ["ISA", "SIPP", "GIA", "Other"]

        print("\nTax wrappers:")
        for idx, wrapper in enumerate(wrappers, 1):
            print(f"  {idx}. {wrapper}")

        while True:
            try:
                choice = input("\nSelect tax wrapper number: ").strip()
                idx = int(choice)
                if 1 <= idx <= len(wrappers):
                    if wrappers[idx - 1] == "Other":
                        custom = input("Enter tax wrapper: ").strip()
                        return custom if custom else wrappers[idx - 1]
                    return wrappers[idx - 1]
                else:
                    print(f"⚠ Please enter a number between 1 and {len(wrappers)}")
            except ValueError:
                print("⚠ Please enter a valid number")

    def get_transaction_type(self) -> str:
        """Get transaction type (BUY/SELL)."""
        print("\n" + "=" * 80)
        print("TRANSACTION TYPE")
        print("=" * 80)

        print("\n  1. BUY")
        print("  2. SELL")

        while True:
            try:
                choice = input("\nSelect transaction type (1 or 2): ").strip()
                if choice == "1":
                    return "BUY"
                elif choice == "2":
                    return "SELL"
                else:
                    print("⚠ Please enter 1 for BUY or 2 for SELL")
            except ValueError:
                print("⚠ Please enter 1 or 2")

    def get_float_input(self, prompt: str, field_name: str) -> float:
        """Get and validate float input."""
        while True:
            try:
                value = input(f"{prompt}: ").strip()
                float_value = float(value)
                if float_value <= 0:
                    print(f"⚠ {field_name} must be greater than 0")
                    continue
                return float_value
            except ValueError:
                print(f"⚠ Please enter a valid number for {field_name}")

    def get_currency(self) -> str:
        """Get currency selection."""
        print("\n" + "=" * 80)
        print("CURRENCY")
        print("=" * 80)

        currencies = ["GBP", "USD", "EUR"]

        print("\nCurrencies:")
        for idx, currency in enumerate(currencies, 1):
            print(f"  {idx}. {currency}")

        while True:
            try:
                choice = input("\nSelect currency number (or press Enter for GBP): ").strip()

                if not choice:
                    print("✓ Using GBP")
                    return "GBP"

                idx = int(choice)
                if 1 <= idx <= len(currencies):
                    return currencies[idx - 1]
                else:
                    print(f"⚠ Please enter a number between 1 and {len(currencies)}")
            except ValueError:
                print("⚠ Please enter a valid number or press Enter for GBP")

    def confirm_transaction(self, transaction: Dict) -> bool:
        """Show transaction summary and get confirmation."""
        print("\n" + "=" * 80)
        print("TRANSACTION SUMMARY")
        print("=" * 80)

        print(f"\n  Date:             {transaction['date']}")
        print(f"  Platform:         {transaction['platform']}")
        print(f"  Tax Wrapper:      {transaction['tax_wrapper']}")
        print(f"  Fund Name:        {transaction['fund_name']}")
        print(f"  Type:             {transaction['transaction_type']}")
        print(f"  Units:            {transaction['units']:,.4f}")
        print(f"  Price per Unit:   {transaction['currency']}{transaction['price_per_unit']:,.2f}")
        print(f"  Total Value:      {transaction['currency']}{transaction['value']:,.2f}")
        print(f"  Currency:         {transaction['currency']}")

        print("\n" + "=" * 80)

        while True:
            confirm = input("\nConfirm and add this transaction? (yes/no): ").strip().lower()
            if confirm in ["yes", "y"]:
                return True
            elif confirm in ["no", "n"]:
                return False
            else:
                print("⚠ Please enter 'yes' or 'no'")

    def get_ticker_for_fund(self, fund_name: str) -> Optional[str]:
        """Get ticker symbol for a fund name."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT ticker FROM fund_ticker_mapping
            WHERE fund_name = ?
            LIMIT 1
        """,
            (fund_name,),
        )

        result = cursor.fetchone()
        return result["ticker"] if result else None

    def update_current_holdings(self, transaction: Dict) -> bool:
        """Update current_holdings.json with the new transaction."""
        holdings_file = Path("data/current_holdings.json")

        # Get ticker for this fund
        ticker = self.get_ticker_for_fund(transaction["fund_name"])

        if not ticker:
            print(f"\n⚠ Warning: No ticker mapping found for '{transaction['fund_name']}'")
            print("  Current holdings JSON will NOT be updated.")
            print("  Transaction was still added to the database.")
            return False

        try:
            # Load existing holdings
            if holdings_file.exists():
                with open(holdings_file, "r") as f:
                    holdings = json.load(f)
            else:
                holdings = {}

            # Initialize ticker entry if it doesn't exist
            if ticker not in holdings:
                holdings[ticker] = {"holdings": []}

            # Find or create the holding entry for this platform/wrapper combination
            platform = transaction["platform"]
            tax_wrapper = transaction["tax_wrapper"]
            units_change = transaction["units"]

            # For SELL transactions, units should be negative
            if transaction["transaction_type"] == "SELL":
                units_change = -units_change

            # Look for existing holding with same platform and tax_wrapper
            found = False
            for holding in holdings[ticker]["holdings"]:
                if holding["platform"] == platform and holding["tax_wrapper"] == tax_wrapper:
                    # Update existing holding
                    old_units = holding["units"]
                    holding["units"] = old_units + units_change
                    found = True
                    print(f"\n✓ Updated holdings: {old_units:.4f} → {holding['units']:.4f} units")

                    # Remove holding if units reach zero or negative
                    if holding["units"] <= 0:
                        holdings[ticker]["holdings"].remove(holding)
                        print(f"  └─ Removed holding (units now {holding['units']:.4f})")
                        # Clean up ticker if no holdings left
                        if not holdings[ticker]["holdings"]:
                            del holdings[ticker]
                            print(f"  └─ Removed ticker {ticker} (no holdings remaining)")
                    break

            if not found:
                # Create new holding entry
                if units_change > 0:  # Only add if positive (BUY)
                    new_holding = {
                        "tax_wrapper": tax_wrapper,
                        "platform": platform,
                        "units": units_change,
                    }
                    holdings[ticker]["holdings"].append(new_holding)
                    print(f"\n✓ Created new holding: {units_change:.4f} units")
                else:
                    print("\n⚠ Warning: SELL transaction but no existing holding found")
                    print(f"  Units change: {units_change:.4f}")
                    print("  Current holdings JSON was NOT updated for this SELL.")
                    return False

            # Save updated holdings
            holdings_file.parent.mkdir(parents=True, exist_ok=True)
            with open(holdings_file, "w") as f:
                json.dump(holdings, f, indent=2)

            print(f"✓ Current holdings JSON updated: {holdings_file}")
            return True

        except Exception as e:
            print(f"\n✗ Error updating current holdings: {e}")
            import traceback

            traceback.print_exc()
            return False

    def insert_transaction(self, transaction: Dict) -> bool:
        """Insert transaction into database."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO transactions (
                    date, platform, tax_wrapper, fund_name,
                    transaction_type, units, price_per_unit, value, currency
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    transaction["date"],
                    transaction["platform"],
                    transaction["tax_wrapper"],
                    transaction["fund_name"],
                    transaction["transaction_type"],
                    transaction["units"],
                    transaction["price_per_unit"],
                    transaction["value"],
                    transaction["currency"],
                ),
            )

            self.conn.commit()
            return True

        except Exception as e:
            print(f"\n✗ Error inserting transaction: {e}")
            self.conn.rollback()
            return False

    def run(self):
        """Run the interactive transaction entry process."""
        print("\n" + "=" * 80)
        print("📝 INTERACTIVE TRANSACTION ENTRY")
        print("=" * 80)
        print("\nAdd a new transaction to your portfolio database.")
        print("Press Ctrl+C at any time to cancel.\n")

        try:
            # Collect transaction details
            transaction = {}

            transaction["date"] = self.get_date()
            transaction["platform"] = self.get_platform()
            transaction["tax_wrapper"] = self.get_tax_wrapper()
            transaction["fund_name"] = self.select_fund()
            transaction["transaction_type"] = self.get_transaction_type()

            print("\n" + "=" * 80)
            print("TRANSACTION DETAILS")
            print("=" * 80)

            transaction["units"] = self.get_float_input("\nEnter number of units", "Units")
            transaction["price_per_unit"] = self.get_float_input(
                "Enter price per unit", "Price per unit"
            )
            transaction["currency"] = self.get_currency()

            # Calculate total value
            transaction["value"] = transaction["units"] * transaction["price_per_unit"]

            # Confirm and insert
            if self.confirm_transaction(transaction):
                if self.insert_transaction(transaction):
                    print("\n✓ Transaction added successfully!")
                    print(
                        f"✓ Added {transaction['transaction_type']} of {transaction['units']:.4f} units"
                    )
                    print(f"✓ Total value: {transaction['currency']}{transaction['value']:,.2f}")

                    # Update current holdings JSON
                    self.update_current_holdings(transaction)

                    # Ask if user wants to add another
                    print("\n" + "=" * 80)
                    add_another = input("\nAdd another transaction? (yes/no): ").strip().lower()
                    if add_another in ["yes", "y"]:
                        print("\n")
                        self.run()  # Recursive call for another transaction
                else:
                    print("\n✗ Failed to add transaction.")
            else:
                print("\n✗ Transaction cancelled.")

        except KeyboardInterrupt:
            print("\n\n✗ Transaction entry cancelled by user.")
            sys.exit(0)

        except Exception as e:
            print(f"\n✗ Unexpected error: {e}")
            import traceback

            traceback.print_exc()


def main():
    """Main execution function."""
    entry = TransactionEntry()

    try:
        entry.run()
    finally:
        entry.close()
        print("\n" + "=" * 80)
        print("Session ended. Thank you!")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
