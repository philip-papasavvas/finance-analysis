# CLAUDE.md - Project Context for Claude Code

## Project Overview

This is a **Portfolio Fund Viewer** - a Python application for analysing investment portfolio transactions from UK trading platforms. It uses Streamlit for the web dashboard and SQLite for data storage.

## Supported Platforms

- **Fidelity** - Transaction history CSVs
- **Interactive Investor** - ISA/SIPP transaction exports
- **InvestEngine** - Trading statement CSVs (GIA and ISA)
- **DODL** - Manual JSON entry (no CSV export available)

## Key Files

| File | Purpose |
|------|---------|
| `portfolio/core/database.py` | Core database class - all CRUD operations |
| `portfolio/loaders/` | Platform-specific CSV parsers (Fidelity, II, InvestEngine) |
| `src/load_transactions.py` | Main transaction loading script |
| `src/load_dodl_transactions.py` | DODL transaction loader from JSON |
| `src/apply_fund_mapping.py` | Applies fund name mappings from JSON |
| `src/validate_database.py` | Database integrity validation |
| `scripts/update_prices.py` | **CLI tool for price updates** (date ranges, backfill, dry-run) |
| `app/portfolio_viewer.py` | **Streamlit web dashboard** with Current Holdings landing page |
| `data/current_holdings.json` | Current holdings by ticker (manually maintained) |
| `data/dodl_transactions.json` | DODL transactions for manual loading |
| `mappings/fund_rename_mapping.json` | Fund name standardization mappings |
| `DATABASE_SCHEMA.md` | Full database schema documentation |

## Database

SQLite database at `portfolio.db` with tables:
- `transactions` - Core transaction data
- `price_history` - Daily closing prices (from yfinance)
- `fund_ticker_mapping` - Links fund names to tickers (includes `vip` flag for priority funds)
- `mapping_status` - Transaction date ranges per ticker

**VIP Fund System**: Tickers marked with `vip=1` in `fund_ticker_mapping` appear on the Current Holdings landing page. This allows focusing on priority investments.

See `DATABASE_SCHEMA.md` for full schema details.

## Common Commands

```bash
# Load transactions from CSV files
python src/load_transactions.py

# Load DODL transactions from JSON
python src/load_dodl_transactions.py data/dodl_transactions.json

# Apply fund name mappings
python src/apply_fund_mapping.py

# Update price data (recommended - has CLI options)
python scripts/update_prices.py                    # Last 30 days, all tickers
python scripts/update_prices.py --dry-run          # Preview without changes
python scripts/update_prices.py --backfill --min-date 2019-01-01  # Full backfill
python scripts/update_prices.py --tickers SMT.L    # Specific ticker

# Legacy price download (simpler, fewer options)
python src/download_ticker_data.py

# Validate database integrity
python src/validate_database.py

# Run the web dashboard
streamlit run app/portfolio_viewer.py

# Query database directly
sqlite3 portfolio.db
```

## Dashboard Structure

The Streamlit dashboard has 5 tabs:

1. **Current Holdings** (Landing Page) - VIP funds overview
   - Total portfolio value and fund count metrics
   - Horizontal stacked bar chart showing holdings by fund and tax wrapper
   - Detailed holdings table with filtering (ISA/SIPP/GIA checkboxes)
   - Color-coded tax wrappers and progress bars for portfolio allocation
   - Reads from `data/current_holdings.json` (manually maintained)

2. **Portfolio Overview** - Complete fund list with transaction counts

3. **Fund Breakdown** - Detailed analysis of individual funds
   - Transaction timeline and cumulative units charts
   - Buy/sell metrics and full transaction history

4. **Price History** - Price charts with buy/sell markers
   - Yearly performance analysis
   - Toggle for transaction overlays

5. **Mapping Status** - Fund-to-ticker mapping overview
   - Shows which funds have price history
   - VIP flag indicators

## Code Style Preferences

### General Principles
- **Separation of concerns**: Keep SQL queries in separate files (`sql.py`), not hardcoded in functions
- **Modularity**: Break large files into smaller, focused modules (e.g., split 1,300+ line files into <300 line modules)
- **Explicit user confirmation**: Always ask before making git commits or major structural changes
- **Deprecate rather than delete**: When removing functionality, add deprecation warnings and keep code for reference
- **Option B approach**: When cleaning up, prefer "remove + deprecate" over "keep as legacy" or "consolidate"

### Code Organization
- **Functional organization**: Organize by functionality (data/, charts/, tabs/) rather than technical layers
- **Small, focused files**: Each file should have a single, clear purpose
- **Clear module boundaries**: Use `__init__.py` with explicit `__all__` exports
- **Constants for configuration**: Extract magic values into named constants (e.g., `WRAPPER_COLORS`, `TICKER_CURRENCY_MAP`)

### Code Quality
- **Type hints**: Use type hints for function parameters and return values (e.g., `-> pd.DataFrame`)
- **Descriptive names**: Use clear, descriptive function names (e.g., `get_all_funds_from_db()`, `render_current_holdings_tab()`)
- **Comprehensive docstrings**: Add docstrings explaining what functions do, not just what they contain
- **Clean imports**: Organize imports logically (standard library, third-party, local)

### Scripts & Tools
- **CLI scripts with clear output**: Use logging with clear formatting (✓, ⊘, ✗ symbols)
- **Standalone validation**: Prefer standalone CLI scripts over methods embedded in classes
- **Interactive workflows**: For data entry, prefer interactive prompts with validation over manual file editing

## Data Flow

1. **CSV Loading**: `load_transactions.py` → parses CSVs via loaders → inserts into `transactions` table
2. **DODL Loading**: `load_dodl_transactions.py` → reads `data/dodl_transactions.json` → inserts into `transactions` table
3. **Fund Mapping**: `apply_fund_mapping.py` → reads `fund_rename_mapping.json` → updates `transactions.mapped_fund_name`
4. **Ticker Mapping**: Manual entries in `fund_ticker_mapping` table link funds to price tickers
5. **Price Download**: `scripts/update_prices.py` → fetches from yfinance → stores in `price_history`
6. **Current Holdings**: `data/current_holdings.json` (manually maintained) → dashboard reads for VIP fund display
7. **Validation**: `validate_database.py` → checks for orphans, duplicates, missing data

## Task Tracking

Project tasks are tracked in `todo.md` with sections:
1. Price Data Management Script
2. Core Holdings Verification
3. Cloud Deployment
4. Database Schema Cleanup (recently completed)

## Package Structure

The project uses a `portfolio` package with the following structure:
- `portfolio/core/database.py` - Core TransactionDatabase class
- `portfolio/loaders/` - Platform-specific CSV parsers
- `portfolio/utils/` - Utility functions

The package is installed in editable mode using `uv pip install -e .` (this project uses `uv` for package management).

## Notes

- **Package structure** (2025-12-22): Code reorganized into `portfolio` package; `pyproject.toml` updated to properly include the package
- **Database cleanup** (2025-12-22): The `fund_name_mapping` table was removed - it was unused
- **Current Holdings**: New landing page displays VIP funds from `data/current_holdings.json` (manually maintained with ticker, units, platform, tax wrapper)
- **DODL support**: Added manual JSON loader for DODL transactions (platform doesn't provide CSV exports)
- **VIP fund system**: Funds marked with `vip=1` in `fund_ticker_mapping` appear on the Current Holdings page
- Fund name mappings live in `mappings/fund_rename_mapping.json` and are applied to `transactions.mapped_fund_name`
- FDTEC ticker was replaced with LU1033663649 for Fidelity Global Tech
- The project uses UK conventions (GBP, ISA/SIPP/GIA tax wrappers)
- `current_holdings.json` format: Grouped by ticker with nested holdings array including tax_wrapper, platform, and units
