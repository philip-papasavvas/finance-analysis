#!/usr/bin/env python3
"""
Load DODL transactions from JSON file into the database.
Handles data cleaning (currency symbols, commas) and calculates price_per_unit.
"""

import json
import sqlite3
from pathlib import Path


def clean_value(value_str: str) -> float:
    """Remove £ symbol and commas, convert to float."""
    return float(value_str.replace('£', '').replace(',', ''))


def load_dodl_transactions(json_path: str, db_path: str = 'portfolio.db'):
    """Load DODL transactions from JSON file into database."""

    # Load JSON
    with open(json_path, 'r') as f:
        transactions = json.load(f)

    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    inserted = 0
    skipped = 0

    for txn in transactions:
        # Clean and calculate values
        value = clean_value(txn['value'])
        units = txn['units']
        price_per_unit = round(value / units, 2) if units > 0 else 0

        try:
            cursor.execute("""
                INSERT INTO transactions (
                    platform, tax_wrapper, date, fund_name,
                    transaction_type, units, price_per_unit, value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                txn['platform'],
                txn['tax_wrapper'],
                txn['date'],
                txn['fund_name'],
                txn['transaction_type'],
                units,
                price_per_unit,
                value
            ))
            inserted += 1
            print(f"✓ Inserted {txn['transaction_type']} {units} units on {txn['date']} (£{value:,.2f})")

        except sqlite3.IntegrityError as e:
            skipped += 1
            print(f"⊘ Skipped duplicate: {txn['date']} {txn['transaction_type']} {units} units - {e}")

    conn.commit()
    conn.close()

    print(f"\n{'='*60}")
    print(f"Summary: {inserted} inserted, {skipped} skipped")
    print(f"{'='*60}")

    return inserted, skipped


if __name__ == '__main__':
    json_file = 'data/dodl_transactions.json'

    if not Path(json_file).exists():
        print(f"Error: {json_file} not found")
        exit(1)

    print(f"Loading DODL transactions from {json_file}...")
    load_dodl_transactions(json_file)