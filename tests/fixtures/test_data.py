"""Shared test data constants and fixtures."""

from datetime import date
from decimal import Decimal

from portfolio.core.models import (
    CashFlow,
    Platform,
    TaxWrapper,
)

# Test dates
TEST_DATE_1 = date(2024, 1, 15)
TEST_DATE_2 = date(2024, 2, 20)
TEST_DATE_3 = date(2024, 3, 10)
TEST_DATE_4 = date(2023, 12, 1)

# Test amounts
TEST_AMOUNT_1 = Decimal("1000.00")
TEST_AMOUNT_2 = Decimal("2500.50")
TEST_AMOUNT_3 = Decimal("500.25")
TEST_AMOUNT_NEGATIVE = Decimal("-1000.00")

# Test quantities
TEST_UNITS_1 = Decimal("100.00")
TEST_UNITS_2 = Decimal("250.50")
TEST_UNITS_FRACTIONAL = Decimal("33.333333")

# Test prices
TEST_PRICE_1 = Decimal("10.50")
TEST_PRICE_2 = Decimal("25.75")
TEST_PRICE_3 = Decimal("0.162")  # Pence format
TEST_PRICE_POUNDS = Decimal("162")  # Pounds format

# Test fund names
TEST_FUND_NAME_1 = "Vanguard FTSE All-World Index Fund"
TEST_FUND_NAME_2 = "iShares Core MSCI World UCITS ETF"
TEST_FUND_NAME_3 = "Fidelity Global Tech Fund"
TEST_FUND_NAME_NORMALISED = "Vanguard Index"  # Normalised version

# Test platforms
TEST_PLATFORM_FIDELITY = Platform.FIDELITY
TEST_PLATFORM_II = Platform.INTERACTIVE_INVESTOR
TEST_PLATFORM_IE = Platform.INVEST_ENGINE

# Test tickers
TEST_TICKER_1 = "VWRP.L"
TEST_TICKER_2 = "EUNL.L"
TEST_TICKER_3 = "BRK-B"  # US ticker
TEST_TICKER_EUR = "MWOT.DE"  # EUR ticker
TEST_ISIN_1 = "IE00B4L5Y983"
TEST_ISIN_2 = "IE0008471009"

# Test tax wrappers
TEST_WRAPPER_ISA = TaxWrapper.ISA
TEST_WRAPPER_SIPP = TaxWrapper.SIPP
TEST_WRAPPER_GIA = TaxWrapper.GIA

# Exchange rates
TEST_USD_RATE = Decimal("0.7426")
TEST_EUR_RATE = Decimal("0.8671")

# Sample transaction dictionaries
SAMPLE_TRANSACTION_1 = {
    "date": TEST_DATE_1,
    "fund_name": TEST_FUND_NAME_1,
    "mapped_fund_name": TEST_FUND_NAME_1,
    "transaction_type": "BUY",
    "units": TEST_UNITS_1,
    "amount": TEST_AMOUNT_1,
    "platform": TEST_PLATFORM_FIDELITY,
    "tax_wrapper": TEST_WRAPPER_ISA,
}

SAMPLE_TRANSACTION_2 = {
    "date": TEST_DATE_2,
    "fund_name": TEST_FUND_NAME_2,
    "mapped_fund_name": TEST_FUND_NAME_2,
    "transaction_type": "SELL",
    "units": TEST_UNITS_2,
    "amount": TEST_AMOUNT_2,
    "platform": TEST_PLATFORM_II,
    "tax_wrapper": TEST_WRAPPER_SIPP,
}

SAMPLE_TRANSACTION_3 = {
    "date": TEST_DATE_3,
    "fund_name": TEST_FUND_NAME_3,
    "mapped_fund_name": TEST_FUND_NAME_3,
    "transaction_type": "BUY",
    "units": TEST_UNITS_FRACTIONAL,
    "amount": TEST_AMOUNT_3,
    "platform": TEST_PLATFORM_IE,
    "tax_wrapper": TEST_WRAPPER_GIA,
}

# Sample price data
SAMPLE_PRICE_DATA_1 = {
    "ticker": TEST_TICKER_1,
    "date": TEST_DATE_1,
    "price": TEST_PRICE_1,
}

SAMPLE_PRICE_DATA_2 = {
    "ticker": TEST_TICKER_2,
    "date": TEST_DATE_2,
    "price": TEST_PRICE_2,
}

# Sample CSV lines
FIDELITY_CSV_HEADER = "Date,Account,Description,Units,Amount,Status"
FIDELITY_CSV_ROW_BUY = (
    f"15/01/2024,ISA,Buy - {TEST_FUND_NAME_1},{TEST_UNITS_1},£{TEST_AMOUNT_1},Completed"
)
FIDELITY_CSV_ROW_SELL = (
    f"20/02/2024,SIPP,Sell - {TEST_FUND_NAME_2},{TEST_UNITS_2},£{TEST_AMOUNT_2},Completed"
)

II_CSV_HEADER = "Date,Description,Debit,Credit,SEDOL"
II_CSV_ROW_BUY = f"15/01/2024,{TEST_FUND_NAME_1},{TEST_AMOUNT_1},,0000001"
II_CSV_ROW_SELL = f"20/02/2024,{TEST_FUND_NAME_2},,{TEST_AMOUNT_2},0000002"

IE_CSV_HEADER = "Date,Fund Name,Quantity,Price,Type"
IE_CSV_ROW_BUY = f"15/01/2024,{TEST_FUND_NAME_1},{TEST_UNITS_1},{TEST_PRICE_1},Buy"
IE_CSV_ROW_SELL = f"20/02/2024,{TEST_FUND_NAME_2},{TEST_UNITS_2},{TEST_PRICE_2},Sell"

# Sample cash flows (for return calculations)
# Negative amount = money in (contribution), positive = money out (withdrawal)
SAMPLE_CASHFLOW_1 = CashFlow(
    date=TEST_DATE_1,
    amount=-1000.00,  # Contribution
    description="Initial investment",
)

SAMPLE_CASHFLOW_2 = CashFlow(
    date=TEST_DATE_2,
    amount=-5000.00,  # Additional contribution
    description="Annual contribution",
)

SAMPLE_CASHFLOW_3 = CashFlow(
    date=TEST_DATE_3,
    amount=500.00,  # Withdrawal
    description="Partial withdrawal",
)

# Sample cash flow list
SAMPLE_CASHFLOWS_LIST = [SAMPLE_CASHFLOW_1, SAMPLE_CASHFLOW_2, SAMPLE_CASHFLOW_3]
