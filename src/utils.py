"""
Utility functions for portfolio analyzer.

Contains helpers for parsing dates, monetary values, and other common operations.
"""
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd


logger = logging.getLogger(__name__)


def parse_date(
    value: str,
    formats: Optional[list[str]] = None,
) -> Optional[date]:
    """
    Parse a date string into a date object.

    Args:
        value: The date string to parse.
        formats: List of date formats to try. Defaults to common UK formats.

    Returns:
        Parsed date or None if parsing fails.
    """
    if pd.isna(value) or not value:
        return None

    if formats is None:
        formats = [
            "%d/%m/%Y",           # 16/01/2023
            "%d %b %Y",           # 16 Jan 2023
            "%Y-%m-%d",           # 2023-01-16
            "%d-%m-%Y",           # 16-01-2023
            "%d/%m/%y %H:%M:%S",  # 16/01/23 15:30:45 (InvestEngine format)
            "%d/%m/%y",           # 16/01/23
        ]

    value = str(value).strip()

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    logger.warning(f"Could not parse date: {value}")
    return None


def parse_money(value: str | float) -> float:
    """
    Parse a monetary value string into a float.

    Handles currency symbols, commas, and various formats.

    Args:
        value: The monetary value to parse (e.g., "£1,234.56", "1234.56", "-£500").

    Returns:
        Parsed float value, or 0.0 if parsing fails.
    """
    if pd.isna(value):
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    # Convert to string and clean
    value = str(value).strip()

    if value.lower() == "n/a" or value == "":
        return 0.0

    # Check for negative (handle both "-£500" and "£-500")
    is_negative = "-" in value

    # Remove currency symbols and formatting
    cleaned = re.sub(r"[£€$,\-\s]", "", value)

    try:
        result = float(cleaned)
        return -result if is_negative else result
    except ValueError:
        logger.warning(f"Could not parse monetary value: {value}")
        return 0.0


def parse_quantity(value: str | float) -> float:
    """
    Parse a quantity/units value.

    Args:
        value: The quantity to parse.

    Returns:
        Parsed float value, or 0.0 if parsing fails.
    """
    if pd.isna(value):
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()

    if value.lower() == "n/a" or value == "":
        return 0.0

    # Remove commas
    cleaned = value.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        logger.warning(f"Could not parse quantity: {value}")
        return 0.0


def parse_price(value: str | float) -> float:
    """
    Parse a price value, handling both pounds and pence.

    Args:
        value: The price to parse (e.g., "£1.62", "162p", "1.62").

    Returns:
        Parsed float value in pounds, or 0.0 if parsing fails.
    """
    if pd.isna(value):
        return 0.0

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()

    if value.lower() == "n/a" or value == "":
        return 0.0

    # Check if price is in pence
    is_pence = "p" in value.lower() and "£" not in value

    # Clean the value
    cleaned = re.sub(r"[£p,\s]", "", value, flags=re.IGNORECASE)

    try:
        result = float(cleaned)
        # Convert pence to pounds if necessary
        return result / 100 if is_pence else result
    except ValueError:
        logger.warning(f"Could not parse price: {value}")
        return 0.0


def find_csv_files(directory: Path, pattern: str) -> list[Path]:
    """
    Find CSV files in a directory matching a glob pattern.

    Args:
        directory: The directory to search.
        pattern: Glob pattern to match (e.g., "*.csv", "TransactionHistory*.csv").

    Returns:
        List of matching file paths, sorted by name.
    """
    if not directory.exists():
        logger.warning(f"Directory does not exist: {directory}")
        return []

    files = sorted(directory.glob(pattern))
    logger.debug(f"Found {len(files)} files matching '{pattern}' in {directory}")
    return files


def normalise_fund_name(name: str) -> str:
    """
    Normalise a fund name for consistent matching.

    Removes extra whitespace, standardises common variations.

    Args:
        name: The fund name to normalise.

    Returns:
        Normalised fund name.
    """
    if not name:
        return ""

    # Strip and collapse whitespace
    normalised = " ".join(name.split())

    # Common substitutions for consistent naming
    substitutions = {
        "WS BLUE": "WS Blue Whale",
        "BLUESTD": "Blue Whale",
        "FDSMITH": "Fundsmith",
        "SCOH MORT": "Scottish Mortgage",
        "SCOTTISH MORTGAGE": "Scottish Mortgage",
        "FIDY FUNDSTD": "Fidelity Funds",
        "ISHS PHYSETCMD": "iShares Physical Gold",
        "ISHARES GBL EN": "iShares Global Clean Energy",
        "POLAR CAP TECH": "Polar Capital Technology",
        "LIONT SPEC SIT": "Liontrust Special Situations",
    }

    upper_name = normalised.upper()
    for pattern, replacement in substitutions.items():
        if pattern in upper_name:
            return replacement

    return normalised


def calculate_years_between(start: date, end: date) -> float:
    """
    Calculate the number of years between two dates.

    Args:
        start: Start date.
        end: End date.

    Returns:
        Number of years as a float.
    """
    return (end - start).days / 365.25


if __name__ == "__main__":
    # Example usage
    import logging
    logging.basicConfig(level=logging.DEBUG)

    print("Date parsing examples:")
    print(f"  '16/01/2023' -> {parse_date('16/01/2023')}")
    print(f"  '16 Jan 2023' -> {parse_date('16 Jan 2023')}")
    print(f"  '2023-01-16' -> {parse_date('2023-01-16')}")

    print()
    print("Money parsing examples:")
    print(f"  '£1,234.56' -> {parse_money('£1,234.56')}")
    print(f"  '-£500.00' -> {parse_money('-£500.00')}")
    print(f"  'n/a' -> {parse_money('n/a')}")
    print(f"  1234.56 -> {parse_money(1234.56)}")

    print()
    print("Price parsing examples:")
    print(f"  '£1.62' -> {parse_price('£1.62')}")
    print(f"  '162p' -> {parse_price('162p')}")
    print(f"  '1.62' -> {parse_price('1.62')}")

    print()
    print("Quantity parsing examples:")
    print(f"  '1,231.99' -> {parse_quantity('1,231.99')}")
    print(f"  'n/a' -> {parse_quantity('n/a')}")

    print()
    print("Fund name normalisation:")
    print(f"  'WS BLUE WHALE GROWTH' -> {normalise_fund_name('WS BLUE WHALE GROWTH')}")
    print(f"  'FDSMITH EQ I AC' -> {normalise_fund_name('FDSMITH EQ I AC')}")
