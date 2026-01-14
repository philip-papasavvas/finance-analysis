# Portfolio Fund Viewer

A Python web application for analysing investment portfolio transactions from UK trading platforms (Fidelity, Interactive Investor, and InvestEngine). Built with Streamlit and SQLite for interactive fund tracking and visualization.

## Quick Reference - Common Operations

### View Portfolio Dashboard
```bash
streamlit run app/portfolio_viewer.py
```

### Add a New Transaction (Interactive)
```bash
python scripts/add_transaction.py
```
- Prompts for all transaction details (date, platform, fund, units, price, etc.)
- Validates fund names against VIP holdings
- Automatically updates **both** transaction database AND `data/current_holdings.json`
- Shows updated holdings immediately

### Load Transactions from CSV
```bash
# Load from platform CSV exports
python src/load_transactions.py

# Load DODL transactions from JSON
python src/load_dodl_transactions.py data/dodl_transactions.json

# Apply fund name mappings after loading
python src/apply_fund_mapping.py
```

### Update Price Data
```bash
# Update last 30 days for all tickers
python scripts/update_prices.py

# Preview changes without updating (dry-run)
python scripts/update_prices.py --dry-run

# Full backfill from specific date
python scripts/update_prices.py --backfill --min-date 2019-01-01

# Update specific ticker only
python scripts/update_prices.py --tickers NVDA
```

### Validate Database
```bash
python src/validate_database.py
```

### Verify VIP Holdings Data Completeness
```bash
python scripts/verify_vip_data_completeness.py
```

---

## Overview

Portfolio Fund Viewer loads transaction history CSV files from multiple platforms, normalises them into a common format, and provides an interactive web dashboard for:

- Viewing all funds with transaction counts
- Analyzing individual fund performance with buy/sell charts and cumulative holdings
- Mapping fund names to standardized display names
- Excluding funds from the portfolio view
- Exporting transaction data to CSV

## Recent Updates

### Dashboard Redesign - ✅ COMPLETED (2025-12-22)

The Streamlit dashboard has been redesigned with a new Current Holdings landing page:

**Completed:**
1. ✅ **Current holdings data** stored in `data/current_holdings.json` (manually maintained)
2. ✅ **Current Holdings landing page** with total portfolio value and metrics
3. ✅ **Current value calculations** using latest prices from price_history
4. ✅ **Portfolio visualizations** - horizontal stacked bar chart and detailed table
5. ✅ **Tax wrapper filtering** - ISA/SIPP/GIA checkboxes for table filtering
6. ✅ **Set as default landing page** - Current Holdings is now Tab 1

### Other Recent Completions
- ✅ **DODL transaction support** - Manual JSON loader for platforms without CSV exports
- ✅ **VIP fund flagging system** - Priority tickers marked with `vip=1` in fund_ticker_mapping
- ✅ **Package reorganization** - Code moved to `portfolio/` package structure
- ✅ **Database schema cleanup** - Removed unused fund_name_mapping table
- ✅ **Price update CLI tool** - `scripts/update_prices.py` with advanced options

---

## Project Status & To-Do

### ✅ Completed

#### Database Schema Cleanup & Documentation (2025-12-22)
- ✅ Removed unused `fund_name_mapping` table
- ✅ Deleted FDTEC ticker entries (replaced with LU1033663649)
- ✅ Created comprehensive DATABASE_SCHEMA.md documentation
- ✅ Added inline docstrings to database methods
- ✅ Built validation script (`src/validate_database.py`)
- ✅ Fixed Amundi ticker (MWOT.DE) and backfilled price data
- ✅ Added ticker mappings: LU1033663649, SUUS.L, SMT.L

#### Price Data Management
- ✅ Created `scripts/update_prices.py` CLI tool with:
  - Date range parameters (--min-date, --max-date)
  - Backfill mode for historical imports
  - Dry-run preview mode
  - Ticker selection and rate limiting

#### Core Holdings Identification
- ✅ Defined criteria for "important" holdings using VIP flag system
- ✅ Generated list of priority tickers/ISINs (15 VIP holdings in `fund_ticker_mapping`)
- ✅ Created mapping infrastructure with `fund_ticker_mapping` and `mapping_status` tables
- ✅ Implemented `data/current_holdings.json` for manual holdings tracking

### 🔄 In Progress

#### 1. Core Holdings Data Completeness Verification
**Priority: High**

**1.1 Verify Data Completeness**
- [ ] Audit which important holdings have complete price history
- [ ] Audit which important holdings have complete transaction records
- [ ] Identify gaps in price data (missing date ranges)
- [ ] Identify gaps in transaction data
- [ ] Create coverage report showing completeness percentage

**1.3 Priority Tickers/ISINs List**
- [ ] Document complete list of priority tickers/ISINs with status
- [ ] Create table showing:
  - Ticker/ISIN
  - Fund Name
  - Has Price History (Yes/No, date range if yes)
  - Has Transactions (Yes/No, count)
  - Data Completeness %
  - Status (Complete / Needs Update / Incomplete)

### 📋 Planned

#### 2. Cloud Deployment & Online Hosting
**Priority: Medium**

**2.1 Infrastructure Setup**
- [ ] Choose cloud provider (AWS, Google Cloud, Azure, Heroku, etc.)
- [ ] Set up cloud database (PostgreSQL, MySQL, or cloud SQLite equivalent)
- [ ] Migrate SQLite database to cloud database
- [ ] Set up secure database connection strings
- [ ] Test data integrity after migration

**2.2 Application Deployment**
- [ ] Deploy Streamlit app to cloud (e.g., Streamlit Cloud, Heroku, Docker container)
- [ ] Configure environment variables for cloud database
- [ ] Test all tabs and functionality in cloud environment
- [ ] Set up automated deployments (CI/CD pipeline)

**2.3 Authentication & Authorization**
- [ ] Implement user authentication (login system)
- [ ] Set up user roles/permissions if multi-user access needed
- [ ] Secure API endpoints and database access
- [ ] Add rate limiting to prevent abuse
- [ ] Implement password management (reset, change, etc.)

**2.4 Security Hardening**
- [ ] Enable HTTPS/SSL certificates
- [ ] Set up firewall rules and network isolation
- [ ] Configure database access controls
- [ ] Enable audit logging for data access
- [ ] Set up automated backups
- [ ] Document security policies

**2.5 Monitoring & Maintenance**
- [ ] Set up application monitoring (uptime, errors, performance)
- [ ] Configure alerts for critical issues
- [ ] Set up database backup schedule (daily minimum)
- [ ] Document disaster recovery procedures
- [ ] Plan for regular security updates

**2.6 Documentation**
- [ ] Create deployment guide
- [ ] Document cloud setup steps
- [ ] Create user guide for accessing cloud version
- [ ] Document backup/restore procedures
- [ ] Create troubleshooting guide

### 🔮 Future Considerations

- [ ] Evaluate SQLAlchemy ORM migration for improved maintainability
- [ ] Additional platform loaders (Hargreaves Lansdown, AJ Bell, Vanguard)
- [ ] HTML/PDF report generation
- [ ] Performance benchmarking against indices
- [ ] Comprehensive unit test coverage

---

## Features

- **Interactive Streamlit Dashboard**: 5-tab interface with Current Holdings landing page, Funds List, Transaction History, Price History, and Mapping Status
- **Current Holdings View**: Real-time portfolio valuation with tax wrapper filtering and allocation visualization
- **Multi-platform support**: Fidelity, Interactive Investor, InvestEngine, and DODL (manual JSON entry)
- **Tax wrapper awareness**: ISA, SIPP, and GIA support with color-coded display
- **Fund name mapping**: Map original fund names to standardized display names via JSON configuration
- **Price history**: Download and store daily price data from Yahoo Finance (yfinance)
- **Fund-to-ticker mapping**: Link funds to tickers for price charts and valuations
- **VIP fund flagging**: Mark priority tickers (`vip=1`) for Current Holdings focus
- **Fund exclusion**: Mark specific funds as excluded from portfolio view
- **Database validation**: Built-in script to check data integrity
- **SQLite database**: Persistent storage with transaction history, price data, and mappings
- **Interactive charts**: Plotly-based buy/sell timeline, cumulative units, and price history charts
- **Type hints**: Full type annotation throughout
- **Logging**: Configurable logging for debugging and monitoring
- **Package management**: Uses `uv` for fast, reliable dependency management

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

# Create virtual environment with uv (recommended)
uv venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install package and dependencies
uv pip install -e .
```

**Note:** This project uses [uv](https://github.com/astral-sh/uv) for fast, reliable package management. All dependencies are defined in `pyproject.toml`.

## Project Structure

```
finance-analysis/
├── portfolio/                    # Main package
│   ├── core/
│   │   └── database.py           # Core database class with CRUD operations
│   ├── loaders/                  # Platform-specific CSV parsers
│   └── utils/                    # Utility functions
├── src/                          # Legacy scripts (being migrated)
│   ├── load_transactions.py      # Main transaction loading script
│   ├── load_dodl_transactions.py # DODL transaction loader from JSON
│   ├── apply_fund_mapping.py     # Apply JSON fund name mappings
│   ├── download_ticker_data.py   # Download price data (legacy)
│   └── validate_database.py      # Database integrity validation
├── scripts/
│   └── update_prices.py          # CLI tool for price updates (recommended)
├── app/
│   └── portfolio_viewer.py       # Streamlit web dashboard (5 tabs)
├── mappings/
│   └── fund_rename_mapping.json  # Fund name mappings (original → display name)
├── data/
│   ├── current_holdings.json     # Current holdings by ticker (manually maintained)
│   ├── dodl_transactions.json    # DODL transactions for manual loading
│   ├── fidelity_*.csv            # Fidelity transaction CSVs
│   ├── ii_*.csv                  # Interactive Investor transaction CSVs
│   └── invest_engine_*.csv       # InvestEngine trading statement CSVs
├── portfolio.db                  # SQLite database file
├── DATABASE_SCHEMA.md            # Database schema documentation
├── CLAUDE.md                     # Project context for Claude Code
└── README.md                     # Project documentation (includes task tracking)
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

The app will open at `http://localhost:8503` with 5 tabs:

- **🏠 Current Holdings**: VIP funds with current values, breakdown charts, and filtering
- **📊 Funds List**: View all funds with transaction counts
- **🔍 Transaction History**: Select individual funds to analyze with charts and transaction details
- **📈 Price History**: Historical price charts with buy/sell markers
- **📋 Mapping Status**: Fund-to-ticker mapping overview

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
