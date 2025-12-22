# CLAUDE.md - Project Context for Claude Code

## Project Overview

This is a **Portfolio Fund Viewer** - a Python application for analysing investment portfolio transactions from UK trading platforms. It uses Streamlit for the web dashboard and SQLite for data storage.

## Supported Platforms

- **Fidelity** - Transaction history CSVs
- **Interactive Investor** - ISA/SIPP transaction exports
- **InvestEngine** - Trading statement CSVs (GIA and ISA)

## Key Files

| File | Purpose |
|------|---------|
| `src/database.py` | Core database class - all CRUD operations |
| `src/loaders.py` | Platform-specific CSV parsers |
| `src/load_transactions.py` | Main transaction loading script |
| `src/apply_fund_mapping.py` | Applies fund name mappings from JSON |
| `src/validate_database.py` | Database integrity validation |
| `scripts/update_prices.py` | **CLI tool for price updates** (date ranges, backfill, dry-run) |
| `app/portfolio_viewer.py` | Streamlit web dashboard |
| `mappings/fund_rename_mapping.json` | Fund name standardization mappings |
| `DATABASE_SCHEMA.md` | Full database schema documentation |

## Database

SQLite database at `portfolio.db` with tables:
- `transactions` - Core transaction data
- `price_history` - Daily closing prices (from yfinance)
- `fund_ticker_mapping` - Links fund names to tickers
- `mapping_status` - Transaction date ranges per ticker

See `DATABASE_SCHEMA.md` for full schema details.

## Common Commands

```bash
# Load transactions from CSV files
python src/load_transactions.py

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

## Code Style Preferences

- **Deprecate rather than delete**: When removing functionality, add deprecation warnings and keep code for reference rather than deleting entirely
- **Comprehensive documentation**: Add docstrings explaining table purposes, not just what they contain
- **CLI scripts with clear output**: Use logging with clear formatting (✓, ⊘, ✗ symbols)
- **Standalone validation**: Prefer standalone CLI scripts over methods embedded in classes
- **Option B approach**: When cleaning up, prefer "remove + deprecate" over "keep as legacy" or "consolidate"

## Data Flow

1. **CSV Loading**: `load_transactions.py` → parses CSVs via loaders → inserts into `transactions` table
2. **Fund Mapping**: `apply_fund_mapping.py` → reads `fund_rename_mapping.json` → updates `transactions.mapped_fund_name`
3. **Ticker Mapping**: Manual entries in `fund_ticker_mapping` table link funds to price tickers
4. **Price Download**: `download_ticker_data.py` → fetches from yfinance → stores in `price_history`
5. **Validation**: `validate_database.py` → checks for orphans, duplicates, missing data

## Task Tracking

Project tasks are tracked in `todo.md` with sections:
1. Price Data Management Script
2. Core Holdings Verification
3. Cloud Deployment
4. Database Schema Cleanup (recently completed)

## Notes

- The `fund_name_mapping` table was **removed** (2025-12-22) - it was unused
- Fund name mappings now live in `mappings/fund_rename_mapping.json` and are applied to `transactions.mapped_fund_name`
- FDTEC ticker was replaced with LU1033663649 for Fidelity Global Tech
- The project uses UK conventions (GBP, ISA/SIPP/GIA tax wrappers)
