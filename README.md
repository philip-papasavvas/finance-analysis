# Portfolio Analyzer

A Python package for analysing investment portfolio transactions from UK trading platforms (Fidelity and Interactive Investor).

## Overview

Portfolio Analyzer loads transaction history CSV files from multiple platforms, normalises them into a common format, and provides tools for:

- Generating transaction reports filtered by fund, platform, or tax wrapper
- Calculating return metrics (simple return, annualised return, MWRR/IRR)
- Tracking positions across ISA and SIPP accounts

## Features

- **Multi-platform support**: Fidelity and Interactive Investor CSV formats
- **Tax wrapper awareness**: ISA, SIPP, and GIA support
- **Flexible reporting**: Filter by fund name, platform, date range, or transaction type
- **Return calculations**: Simple return, annualised return, and Money-Weighted Rate of Return (MWRR/IRR)
- **Type hints**: Full type annotation throughout
- **Logging**: Configurable logging for debugging and monitoring

## Installation

### Dependencies

```
pandas>=2.0.0
scipy>=1.10.0
pyyaml>=6.0
```

### Setup

```bash
# Clone or copy the package
cp -r portfolio_analyzer /path/to/your/project/

# Install dependencies
pip install pandas scipy pyyaml
```

## Project Structure

```
portfolio_analyzer/
├── __init__.py          # Package exports
├── config.py            # YAML configuration loader
├── config.yaml          # Default configuration
├── models.py            # Data models (Transaction, Holding, CashFlow)
├── loaders.py           # Platform-specific CSV parsers
├── reports.py           # Report generation
├── calculators.py       # Return calculations
└── utils.py             # Helper functions
```

## Quick Start

### Loading Transactions

```python
from pathlib import Path
from portfolio_analyzer import FidelityLoader, InteractiveInvestorLoader

# Load Fidelity transactions
fidelity_loader = FidelityLoader(Path("./data/fidelity"))
fidelity_transactions = fidelity_loader.load()

# Load Interactive Investor transactions
ii_loader = InteractiveInvestorLoader(Path("./data/interactive_investor"))
ii_transactions = ii_loader.load()

# Combine all transactions
all_transactions = fidelity_transactions + ii_transactions
```

### Generating Reports

```python
from portfolio_analyzer import TransactionReport, Platform, TaxWrapper

# Create report generator
report = TransactionReport(all_transactions)

# Get all transactions for a specific fund in an ISA
df = report.generate_fund_report(
    fund_name="Global Index Fund",
    platform=Platform.FIDELITY,
    tax_wrapper=TaxWrapper.ISA,
)

print(df)
```

Output:

```
| Tax Wrapper | Platform | Date       | Fund Name         | Buy/Sell | Units    | Price (£) | Value (£) |
|-------------|----------|------------|-------------------|----------|----------|-----------|-----------|
| ISA         | Fidelity | 16/01/2023 | Global Index Fund | Buy      | 1,000.00 | 1.2000    | 1,200.00  |
| ISA         | Fidelity | 28/02/2023 | Global Index Fund | Buy      |   500.00 | 2.0000    | 1,000.00  |
| ...         | ...      | ...        | ...               | ...      | ...      | ...       | ...       |
```

### Calculating Returns

```python
from datetime import date
from portfolio_analyzer import ReturnCalculator, CashFlow

# Define cash flows (negative = money in, positive = money out)
cash_flows = [
    CashFlow(date(2021, 9, 1), -10000.00, "Initial investment"),
    CashFlow(date(2022, 4, 1), -5000.00, "Top up"),
    CashFlow(date(2023, 6, 1), 2000.00, "Withdrawal"),
]

current_value = 15500.00

# Calculate returns
calculator = ReturnCalculator(cash_flows, current_value)
metrics = calculator.calculate_all()

print(metrics)
```

Output:

```
Return Metrics (2021-09-01 to 2025-12-09)
  Total Contributions: £15,000.00
  Total Withdrawals:   £2,000.00
  Current Value:       £15,500.00
  Total Gain:          £2,500.00
  Simple Return:       +16.67%
  Annualised Return:   +3.71%
  MWRR (IRR):          +4.12%
  Years Invested:      4.27
```

### Filtering Transactions

```python
from portfolio_analyzer import TransactionFilter, TransactionReport

report = TransactionReport(transactions)

# Create a filter
criteria = TransactionFilter(
    fund_name="UK Equity Fund",
    tax_wrapper=TaxWrapper.ISA,
    start_date=date(2021, 1, 1),
    end_date=date(2023, 12, 31),
)

# Apply filter
filtered = report.filter(criteria)

# Get summary statistics
summary = report.generate_summary(filtered)
print(f"Total bought: £{summary['total_bought']:,.2f}")
print(f"Total sold: £{summary['total_sold']:,.2f}")
print(f"Units remaining: {summary['units_remaining']:,.2f}")
```

### Listing All Funds

```python
from portfolio_analyzer import get_unique_funds

funds = get_unique_funds(transactions)
for fund in funds:
    print(f"  - {fund}")
```

## Configuration

The package uses a YAML configuration file (`config.yaml`):

```yaml
data:
  base_path: "./data"
  fidelity:
    directory: "fidelity"
    file_pattern: "TransactionHistory*.csv"
    skip_rows: 6
  interactive_investor:
    directory: "interactive_investor"
    file_pattern: "ii_*.csv"
    skip_rows: 0

logging:
  level: "INFO"
  format: "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
  date_format: "%Y-%m-%d %H:%M:%S"

transaction_types:
  buy:
    - "Buy"
    - "Buy For Switch"
    - "Transfer In"
  sell:
    - "Sell"
    - "Sell For Switch"
```

Load configuration:

```python
from portfolio_analyzer import load_config

config = load_config("config.yaml")
print(f"Data path: {config.data.base_path}")
```

## Data Models

### Transaction

Represents a single buy/sell transaction:

```python
@dataclass
class Transaction:
    platform: Platform
    tax_wrapper: TaxWrapper
    date: date
    fund_name: str
    transaction_type: TransactionType
    units: float
    price_per_unit: float
    value: float
    currency: str = "GBP"
    sedol: Optional[str] = None
```

### CashFlow

Represents a cash flow for return calculations:

```python
@dataclass
class CashFlow:
    date: date
    amount: float  # Negative = money in, Positive = money out
    description: str = ""
```

### Enums

```python
class Platform(Enum):
    FIDELITY
    INTERACTIVE_INVESTOR

class TaxWrapper(Enum):
    ISA
    SIPP
    GIA
    OTHER

class TransactionType(Enum):
    BUY
    SELL
    DIVIDEND
    TRANSFER_IN
    TRANSFER_OUT
    FEE
    INTEREST
    SUBSCRIPTION
    OTHER
```

## Data Directory Structure

Organise your CSV files as follows:

```
data/
├── fidelity/
│   ├── TransactionHistory.csv
│   └── TransactionHistory_1.csv
└── interactive_investor/
    ├── ii_isa_2020_2022.csv
    └── ii_isa_2022_2024.csv
```

## Exporting Data

### To CSV

```python
report = TransactionReport(transactions)
criteria = TransactionFilter(fund_name="Global Index Fund")
report.to_csv(Path("fund_transactions.csv"), report.filter(criteria))
```

### To Markdown

```python
markdown_table = report.to_markdown(filtered_transactions)
print(markdown_table)
```

### To DataFrame

```python
df = report.to_dataframe(filtered_transactions)
# Use pandas methods for further analysis
df.groupby("Fund Name")["Value (£)"].sum()
```

## Extending the Package

### Adding a New Platform Loader

1. Create a new class inheriting from `BaseLoader`
2. Implement the required methods:

```python
from portfolio_analyzer.loaders import BaseLoader

class NewPlatformLoader(BaseLoader):
    platform = Platform.NEW_PLATFORM  # Add to Platform enum first

    def load(self) -> list[Transaction]:
        # Load and parse CSV files
        pass

    def _parse_row(self, row: pd.Series) -> Optional[Transaction]:
        # Parse a single row
        pass

    def _determine_tax_wrapper(self, row: pd.Series) -> TaxWrapper:
        # Extract tax wrapper from row
        pass

    def _determine_transaction_type(self, row: pd.Series) -> TransactionType:
        # Extract transaction type from row
        pass
```

## Logging

The package uses Python's built-in `logging` module. Configure the level in `config.yaml`:

```yaml
logging:
  level: "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

Or programmatically:

```python
import logging
logging.getLogger("portfolio_analyzer").setLevel(logging.DEBUG)
```

## License

MIT License - feel free to use and modify as needed.

## Contributing

Contributions welcome! Areas for improvement:

- Additional platform loaders (Hargreaves Lansdown, AJ Bell, Vanguard)
- HTML/PDF report generation
- Chart/visualisation support
- Performance benchmarking against indices
- Unit tests