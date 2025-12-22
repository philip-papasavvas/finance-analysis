# Database Schema Documentation

## Overview

The portfolio analyzer uses SQLite with the following core tables for managing investment transactions, fund mappings, and price history.

---

## Tables

### 1. **transactions** (515 records)
**Purpose**: Core transaction data - all buy/sell transactions from trading platforms

**Columns**:
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| platform | TEXT | Trading platform (FIDELITY, INTERACTIVE_INVESTOR, INVEST_ENGINE) |
| tax_wrapper | TEXT | Account type (ISA, SIPP, GIA, OTHER) |
| date | TEXT | Transaction date (YYYY-MM-DD) |
| fund_name | TEXT | Original fund name from CSV file |
| transaction_type | TEXT | Type of transaction (BUY, SELL, DIVIDEND, etc.) |
| units | REAL | Number of units traded |
| price_per_unit | REAL | Price per unit in GBP |
| value | REAL | Total transaction value in GBP |
| currency | TEXT | Currency (default: GBP) |
| sedol | TEXT | SEDOL code (fund identifier) |
| reference | TEXT | Transaction reference number |
| raw_description | TEXT | Raw description from CSV |
| mapped_fund_name | TEXT | **Standardized fund name** (from fund_rename_mapping.json) |
| excluded | INTEGER | Flag: 1 if fund is excluded from portfolio view, 0 otherwise |
| created_at | TIMESTAMP | When record was inserted |

**Usage**: Primary source for all portfolio calculations and analysis

---

### 2. **fund_ticker_mapping** (14 records)
**Purpose**: Maps fund names to ticker symbols for price data lookup

**Columns**:
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| fund_name | TEXT | Fund name (matches transactions table) |
| ticker | TEXT | Ticker symbol (e.g., SUUS.L, SMT.L, LU1033663649) |
| sedol | TEXT | SEDOL code (optional) |
| isin | TEXT | ISIN code (optional) |
| mapped_fund_name | TEXT | Reserved for future use |
| is_auto_mapped | INTEGER | 1 if auto-extracted, 0 if manually added |
| created_at | TIMESTAMP | When mapping was created |

**Key Points**:
- Each fund_name maps to exactly ONE ticker
- Used by joins to link transactions → price_history data
- Manual additions have is_auto_mapped = 0
- Recent additions: SUUS.L, SMT.L, LU1033663649 (Fidelity Global Tech)

**Usage**: In Streamlit app to fetch price data for charts and analysis

---

### 3. **mapping_status** (10 records)
**Purpose**: Tracking analytics table - shows earliest/latest transaction dates per ticker

**Columns**:
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| ticker | TEXT | Ticker symbol |
| fund_name | TEXT | Associated fund name |
| earliest_date | TEXT | **First transaction date for this ticker** (from transactions table) |
| latest_date | TEXT | **Last transaction date for this ticker** (from transactions table) |
| transaction_count | INTEGER | Total number of transactions for this ticker |
| created_at | TIMESTAMP | When record was created |
| updated_at | TIMESTAMP | Last updated timestamp |

**Key Points**:
- Dates come from **transaction data**, not price data
- Used for portfolio date range analysis
- Helps identify which funds you're actively trading
- Populated by migration script: `src/migrate_ticker_mappings.py`

**Example**:
```
ticker: SMT.L
earliest_date: 2019-04-29  (first transaction)
latest_date: 2023-12-05    (last transaction)
transaction_count: 19
```

**Usage**: Portfolio reporting and analytics

---

### 4. **price_history** (13,091 records)
**Purpose**: Daily closing price data for all tickers

**Columns**:
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| date | TEXT | Price date (YYYY-MM-DD) |
| ticker | TEXT | Ticker symbol |
| fund_name | TEXT | Fund name for reference |
| close_price | REAL | Daily closing price |
| created_at | TIMESTAMP | When record was inserted |

**Unique Constraint**: (date, ticker) - prevents duplicate daily prices

**Data Source**: Downloaded from yfinance (Yahoo Finance)

**Usage**: Plotting charts, performance calculations, current valuations

---

### 5. ~~**fund_name_mapping**~~ (REMOVED - 2025-12-22)
**Status**: 🗑️ **REMOVED FROM SCHEMA**

This table was removed as part of database cleanup. It was never actively used.

**Reason for removal**:
- Table was always empty (0 records)
- Fund name mappings are handled via:
  - `mappings/fund_rename_mapping.json` (source of truth)
  - `transactions.mapped_fund_name` column (applied mappings)
  - `src/apply_fund_mapping.py` (application script)

**Migration notes**:
- Table creation removed from `src/database.py`
- Related methods removed: `add_fund_mapping()`, `get_standardized_name()`, `get_all_fund_mappings()`, `clear_fund_mappings()`
- `populate_fund_mappings()` in `src/standardize_fund_names.py` deprecated

---

## Table Relationships

```
transactions
    ├── fund_name ──→ fund_ticker_mapping.fund_name ──→ ticker
    │                                                      ↓
    │                                          price_history.ticker
    │
    └── mapped_fund_name ──→ mapping_status.fund_name ──→ ticker
                                                            ↓
                                              price_history.ticker
```

---

## Crossover Between fund_ticker_mapping and mapping_status

| Aspect | fund_ticker_mapping | mapping_status |
|--------|-------------------|-----------------|
| **Purpose** | Reference/lookup table | Analytics/reporting table |
| **Data Type** | Structural (fund → ticker mapping) | Statistical (date ranges, counts) |
| **Records** | 1 per unique fund | 1 per unique ticker |
| **Source** | Manual entry + auto-extraction | Aggregated from transactions table |
| **Usage** | SQL joins in queries | Portfolio dashboards & reports |
| **Mutability** | Rarely changes | Updated after new transactions |
| **Key Info** | ticker, sedol, isin | earliest_date, latest_date, count |

**In Practice**:
- `fund_ticker_mapping` = "How do I find the price data for this fund?"
- `mapping_status` = "When did I buy/sell this fund, and how often?"

---

## Data Integrity Notes

1. **Unique Constraints**:
   - transactions: (platform, date, fund_name, transaction_type, value, reference)
   - price_history: (date, ticker)
   - fund_ticker_mapping: (fund_name, ticker)
   - mapping_status: (ticker)

2. **Foreign Key-like Relationships** (not enforced in SQLite):
   - transactions.fund_name → fund_ticker_mapping.fund_name
   - fund_ticker_mapping.ticker → price_history.ticker

3. **Nullable Columns**:
   - transactions.mapped_fund_name (NULL until mapping applied)
   - fund_ticker_mapping.sedol, isin (optional)

---

## Recent Changes (2025-12-22)

- ✓ Added LU1033663649 (Fidelity Global Technology) ticker mapping
- ✓ Added SUUS.L (iShares MSCI USA SRI) ticker mapping
- ✓ Added SMT.L (Scottish Mortgage) ticker mapping
- ✓ Created mapping_status table
- ✓ Downloaded 4,541 price records for new tickers
- ✓ Updated fund_rename_mapping.json with "Fidelity Funds" → "Fidelity Funds - Global Technology Fund W-ACC-GBP"

---

## Queries

### Get all transactions for a ticker
```sql
SELECT t.* FROM transactions t
INNER JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
WHERE ftm.ticker = 'SUUS.L'
ORDER BY t.date;
```

### Get price history for a ticker
```sql
SELECT * FROM price_history
WHERE ticker = 'SUUS.L'
ORDER BY date DESC
LIMIT 30;
```

### Get fund trading activity summary
```sql
SELECT
  ticker,
  fund_name,
  earliest_date,
  latest_date,
  transaction_count
FROM mapping_status
ORDER BY latest_date DESC;
```

---

## Database Statistics

| Metric | Value |
|--------|-------|
| Total Transactions | 515 |
| Unique Funds | ~50 |
| Total Price Records | 13,091 |
| Tickers Mapped | 10 |
| Date Range (Transactions) | 2018-09-18 → 2025-12-22 |
| Date Range (Prices) | 2019-01-02 → 2025-12-22 |
