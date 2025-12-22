# Portfolio Fund Viewer

A Python web application for analysing investment portfolio transactions from UK trading platforms (Fidelity, Interactive Investor, and InvestEngine). Built with Streamlit and SQLite for interactive fund tracking and visualization.

## Overview

Portfolio Fund Viewer loads transaction history CSV files from multiple platforms, normalises them into a common format, and provides an interactive web dashboard for:

- Viewing all funds with transaction counts
- Analyzing individual fund performance with buy/sell charts and cumulative holdings
- Mapping fund names to standardized display names
- Excluding funds from the portfolio view
- Exporting transaction data to CSV

## Features

- **Interactive Streamlit Dashboard**: Two-tab interface with Portfolio Overview and Fund Breakdown
- **Multi-platform support**: Fidelity, Interactive Investor, and InvestEngine CSV formats
- **Tax wrapper awareness**: ISA, SIPP, and GIA support
- **Fund name mapping**: Map original fund names to standardized display names via JSON configuration
- **Price history**: Download and store daily price data from Yahoo Finance (yfinance)
- **Fund-to-ticker mapping**: Link funds to tickers for price charts and valuations
- **Fund exclusion**: Mark specific funds as excluded from portfolio view
- **Database validation**: Built-in script to check data integrity
- **SQLite database**: Persistent storage with transaction history, price data, and mappings
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
yfinance>=0.2.0
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
│   ├── database.py               # SQLite database manager (core CRUD operations)
│   ├── models.py                 # Data models (Transaction, Platform, TaxWrapper enums)
│   ├── loaders.py                # Platform-specific CSV parsers (Fidelity, II, InvestEngine)
│   ├── load_transactions.py      # Main transaction loading script
│   ├── apply_fund_mapping.py     # Apply JSON fund name mappings to transactions
│   ├── download_ticker_data.py   # Download price data from Yahoo Finance (legacy)
│   ├── validate_database.py      # Database integrity validation script
│   ├── migrate_ticker_mappings.py # Migration script for ticker mappings
│   ├── standardize_fund_names.py # Fund name standardization (deprecated)
│   ├── exclude_funds.py          # Fund exclusion utilities
│   ├── migrate_db.py             # Database migration script
│   ├── calculators.py            # Return/performance calculation utilities
│   ├── config.py                 # Configuration loading
│   ├── utils.py                  # Utility functions
│   ├── reports.py                # Report generation utilities
│   └── query_database.py         # Database query utilities
├── scripts/
│   └── update_prices.py          # CLI tool for price updates (recommended)
├── app/
│   └── portfolio_viewer.py       # Streamlit web dashboard
├── mappings/
│   ├── fund_rename_mapping.json  # Fund name mappings (original → display name)
│   └── fund_ticker_mapping.json  # Fund to ticker symbol mappings
├── data/
│   ├── fidelity_*.csv            # Fidelity transaction CSVs
│   ├── ii_*.csv                  # Interactive Investor transaction CSVs
│   └── invest_engine_*.csv       # InvestEngine trading statement CSVs
├── portfolio.db                  # SQLite database file
├── DATABASE_SCHEMA.md            # Database schema documentation
├── CLAUDE.md                     # Project context for Claude Code
├── todo.md                       # Project task tracking
└── README.md
```

### Source Files (`src/`)

| File | Purpose |
|------|---------|
| `database.py` | Core database class with CRUD operations for transactions, prices, and mappings |
| `models.py` | Data models: `Transaction`, `Platform`, `TaxWrapper`, `TransactionType` enums |
| `loaders.py` | CSV parsers for each platform (FidelityLoader, InteractiveInvestorLoader, InvestEngineLoader) |
| `load_transactions.py` | Main script to load all CSV files into the database |
| `apply_fund_mapping.py` | Applies fund_rename_mapping.json to update transactions.mapped_fund_name |
| `download_ticker_data.py` | Downloads historical prices from yfinance and stores in price_history |
| `validate_database.py` | Checks for orphaned funds, duplicate prices, missing data, etc. |
| `migrate_ticker_mappings.py` | Creates mapping_status table and populates date ranges |
| `standardize_fund_names.py` | Legacy script for fund name standardization (deprecated) |
| `exclude_funds.py` | Mark funds as excluded from portfolio views |
| `calculators.py` | XIRR and performance calculation functions |
| `config.py` | YAML configuration loader |
| `reports.py` | Transaction report generation (CSV, Markdown, DataFrame) |

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

### 5. Update Price Data

Use the price update script to download/update historical prices:

```bash
# Update all tickers for the last 30 days
python scripts/update_prices.py

# Update specific date range
python scripts/update_prices.py --min-date 2024-01-01 --max-date 2024-12-31

# Update specific tickers only
python scripts/update_prices.py --tickers SUUS.L SMT.L

# Full historical backfill
python scripts/update_prices.py --backfill --min-date 2019-01-01

# Preview changes without committing (dry run)
python scripts/update_prices.py --dry-run
```

This downloads daily closing prices from Yahoo Finance and stores them in the `price_history` table.

### 6. Validate Database (Optional)

Run the validation script to check for data integrity issues:

```bash
python src/validate_database.py
```

The validator checks for:
- Orphaned funds (transactions without ticker mappings)
- Date range mismatches in mapping_status
- Duplicate price records
- Missing price data for transaction dates
- Ticker consistency across tables

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
    INVEST_ENGINE

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

## Database Schema

The SQLite database (`portfolio.db`) contains the following tables:

| Table | Purpose |
|-------|---------|
| `transactions` | Core buy/sell transaction data from trading platforms |
| `price_history` | Daily closing prices for tickers (from yfinance) |
| `fund_ticker_mapping` | Maps fund names to ticker symbols for price lookup |
| `mapping_status` | Tracks earliest/latest transaction dates per ticker |

For detailed schema documentation, see [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md).

## Data Directory Structure

Place your CSV files in the `data/` directory:

```
data/
├── fidelity_transactions_1.csv          # Fidelity transaction history
├── fidelity_transactions_2.csv
├── ii_isa_20180301_20200301.csv         # Interactive Investor exports
├── ii_isa_20200301_20220301.csv
├── invest_engine_isa_trading_statement.csv  # InvestEngine trading statements
└── invest_engine_gia_trading_statement.csv
```

File naming conventions:
- **Fidelity**: `fidelity*.csv` or `fidelity-transactions*.csv`
- **Interactive Investor**: `ii_*.csv`
- **InvestEngine**: `invest_engine_*.csv`

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