# Portfolio Fund Viewer

A Python web application for analysing investment portfolio transactions from UK trading platforms (Fidelity and Interactive Investor). Built with Streamlit and SQLite for interactive fund tracking and visualization.

## Overview

Portfolio Fund Viewer loads transaction history CSV files from multiple platforms, normalises them into a common format, and provides an interactive web dashboard for:

- Viewing all funds with transaction counts
- Analyzing individual fund performance with buy/sell charts and cumulative holdings
- Mapping fund names to standardized display names
- Excluding funds from the portfolio view
- Exporting transaction data to CSV

## Features

- **Interactive Streamlit Dashboard**: Two-tab interface with Portfolio Overview and Fund Breakdown
- **Multi-platform support**: Fidelity and Interactive Investor CSV formats
- **Tax wrapper awareness**: ISA, SIPP, and GIA support
- **Fund name mapping**: Map original fund names to standardized display names via JSON configuration
- **Fund exclusion**: Mark specific funds as excluded from portfolio view
- **SQLite database**: Persistent storage with transaction history and mappings
- **Interactive charts**: Plotly-based buy/sell timeline and cumulative units charts
- **Type hints**: Full type annotation throughout
- **Logging**: Configurable logging for debugging and monitoring

## Installation

### Dependencies

```
pandas>=2.0.0
scipy>=1.10.0
pyyaml>=6.0
streamlit>=1.28.0
plotly>=5.17.0
```

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd finance-analysis

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install pandas scipy pyyaml streamlit plotly
```

## Project Structure

```
finance-analysis/
├── src/
│   ├── database.py              # SQLite database manager
│   ├── loaders.py               # Platform-specific CSV parsers
│   ├── standardize_fund_names.py # Fund name standardization
│   ├── exclude_funds.py          # Fund exclusion utilities
│   ├── migrate_db.py             # Database migration script
│   └── apply_fund_mapping.py     # Apply JSON fund name mappings
├── app/
│   └── portfolio_viewer.py       # Streamlit web dashboard
├── mappings/
│   └── fund_rename_mapping.json  # Fund name mappings configuration
├── data/
│   ├── fidelity/                 # Fidelity CSV files
│   └── interactive_investor/     # Interactive Investor CSV files
├── portfolio.db                  # SQLite database file
└── README.md
```

## Quick Start

### 1. Load Transaction Data

Place your CSV files in the data directories:
- `data/fidelity/` - Fidelity transaction history CSVs
- `data/interactive_investor/` - Interactive Investor CSVs

Then load them into the database:

```bash
python src/loaders.py
```

This will create or update the `portfolio.db` SQLite database with all transactions.

### 2. Set Up Fund Name Mappings (Optional)

Create a JSON file at `mappings/fund_rename_mapping.json` with fund name mappings:

```json
{
  "Original Fund Name": "Display Name",
  "WS Blue Whale Growth Fund R Acc": "Blue Whale Growth",
  "Vanguard FTSE All-Share Index Fund": "Vanguard UK Equity"
}
```

Apply the mappings:

```bash
python src/apply_fund_mapping.py
```

### 3. Exclude Funds (Optional)

Mark specific funds as excluded from the portfolio view:

```bash
python src/exclude_funds.py
```

Or add exclusions in your code:

```python
from src.database import TransactionDatabase

db = TransactionDatabase("portfolio.db")
db.exclude_fund("Old Fund Name")
db.close()
```

### 4. Run the Dashboard

Start the Streamlit web application:

```bash
streamlit run app/portfolio_viewer.py
```

The app will open at `http://localhost:8501` with two tabs:

- **Portfolio Overview**: View all funds with transaction counts
- **Fund Breakdown**: Select individual funds to analyze with charts and transaction details

### Running the Database Migration

If you need to update an existing database with new columns:

```bash
python src/migrate_db.py
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