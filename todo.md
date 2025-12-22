# Portfolio Viewer - To-Do List

## 1. Price Data Management Script
### 1.1 Create Dynamic Price Update Script ✓
- [x] Design script that accepts minimum and maximum date parameters
- [x] Implement logic to detect missing price data within date range
- [x] Fetch missing price data from yfinance for all tickers/ISINs
- [x] Handle API rate limiting and retries
- [x] Insert/update missing data into price_history table
- [x] Add logging to track which tickers were updated and date ranges

### 1.2 Implement One-Off Backfill Capability ✓
- [x] Create separate function for historical data backfill
- [x] Allow bulk import of historical prices for date ranges
- [x] Add progress indicators for long-running operations
- [x] Validate data before insertion (no duplicates, valid prices)
- [x] Generate report of successfully imported vs failed tickers

### 1.3 Script Entry Point ✓
- [x] Create CLI interface (e.g., `python scripts/update_prices.py --min-date 2020-01-01 --max-date 2025-12-31`)
- [x] Add dry-run mode to preview changes without committing
- [x] Support updating specific tickers vs all tickers
- [x] Add scheduling support (cron job ready - script exits with 0/1 for success/failure)

---

## 2. Core Holdings Price & Transaction Verification
### 2.1 Identify Important Holdings
- [ ] Define criteria for "important" holdings (e.g., > £X value, actively traded, etc.)
- [ ] Generate list of priority tickers/ISINs
- [ ] Create mapping of holdings to tickers/ISINs for easy reference

### 2.2 Verify Data Completeness
- [ ] Audit which important holdings have complete price history
- [ ] Audit which important holdings have complete transaction records
- [ ] Identify gaps in price data (missing date ranges)
- [ ] Identify gaps in transaction data
- [ ] Create coverage report showing completeness %

### 2.3 Priority Tickers/ISINs List
- [ ] Document the complete list of priority tickers/ISINs with status
- [ ] Create table showing:
  - Ticker/ISIN
  - Fund Name
  - Has Price History (Yes/No, date range if yes)
  - Has Transactions (Yes/No, count)
  - Data Completeness %
  - Status (Complete / Needs Update / Incomplete)

---

## 3. Cloud Deployment & Online Hosting
### 3.1 Infrastructure Setup
- [ ] Choose cloud provider (AWS, Google Cloud, Azure, Heroku, etc.)
- [ ] Set up cloud database (PostgreSQL, MySQL, or cloud SQLite equivalent)
- [ ] Migrate SQLite database to cloud database
- [ ] Set up secure database connection strings
- [ ] Test data integrity after migration

### 3.2 Application Deployment
- [ ] Deploy Streamlit app to cloud (e.g., Streamlit Cloud, Heroku, Docker container)
- [ ] Configure environment variables for cloud database
- [ ] Test all tabs and functionality in cloud environment
- [ ] Set up automated deployments (CI/CD pipeline)

### 3.3 Authentication & Authorization
- [ ] Implement user authentication (login system)
- [ ] Set up user roles/permissions if multi-user access needed
- [ ] Secure API endpoints and database access
- [ ] Add rate limiting to prevent abuse
- [ ] Implement password management (reset, change, etc.)

### 3.4 Security Hardening
- [ ] Enable HTTPS/SSL certificates
- [ ] Set up firewall rules and network isolation
- [ ] Configure database access controls
- [ ] Enable audit logging for data access
- [ ] Set up automated backups
- [ ] Document security policies

### 3.5 Monitoring & Maintenance
- [ ] Set up application monitoring (uptime, errors, performance)
- [ ] Configure alerts for critical issues
- [ ] Set up database backup schedule (daily minimum)
- [ ] Document disaster recovery procedures
- [ ] Plan for regular security updates

### 3.6 Documentation
- [ ] Create deployment guide
- [ ] Document cloud setup steps
- [ ] Create user guide for accessing cloud version
- [ ] Document backup/restore procedures
- [ ] Create troubleshooting guide

---

## Priority Order
1. **High Priority:** Price Data Management Script (Item 1)
2. **High Priority:** Core Holdings Verification (Item 2)
3. **Medium Priority:** Cloud Deployment (Item 3)

---

---

## 4. Database Schema Cleanup & Documentation
### 4.1 Remove or Consolidate fund_name_mapping Table
- [ ] Note: `populate_fund_mappings()` in src/standardize_fund_names.py DOES use this table
- [ ] However: src/standardize_fund_names.py is NOT called in current workflow
- [ ] Current workflow uses src/apply_fund_mapping.py instead (updates transactions.mapped_fund_name)
- [ ] Decision options:
  - **Option A**: Keep table but document it as legacy/unused (safer)
  - **Option B**: Remove table + db methods + deprecate src/standardize_fund_names.py (cleaner)
  - **Option C**: Consolidate both pipelines to use fund_name_mapping table consistently
- [ ] If removing: Delete `add_fund_mapping()`, `get_standardized_name()`, `get_all_fund_mappings()`, `clear_fund_mappings()` from database.py
- [ ] If keeping: Document why it exists and when to use it
- **Context**: Table is empty (0 records), used by legacy code path not in current pipeline

### 4.2 Clean Up mapping_status Table
- [ ] Delete old FDTEC entry (replaced with LU1033663649 for Fidelity Global Tech)
- [ ] Delete corresponding FDTEC entry from fund_ticker_mapping
- [ ] Verify no code references FDTEC
- **Query**: `DELETE FROM mapping_status WHERE ticker = 'FDTEC'; DELETE FROM fund_ticker_mapping WHERE ticker = 'FDTEC';`

### 4.3 Add Database Documentation
- [ ] Create DATABASE_SCHEMA.md with table definitions and purposes (✓ Created 2025-12-22)
- [ ] Add inline docstring comments to create_tables() method in database.py
- [ ] Document the distinction between fund_ticker_mapping and mapping_status
- [ ] Update README.md to reference DATABASE_SCHEMA.md
- [ ] Add column-level comments in SQL CREATE TABLE statements
- **Key Distinction**:
  - `fund_ticker_mapping`: Maps fund names → tickers (reference data)
  - `mapping_status`: Tracks earliest/latest transaction dates per ticker (analytics)

### 4.4 Add Data Validation Script
- [ ] Create src/validate_database.py script
- [ ] Check for orphaned records (funds with no ticker mapping)
- [ ] Verify transaction dates against mapping_status
- [ ] Check for duplicate price history records
- [ ] Generate validation report

### 4.5 Consider SQLAlchemy ORM Migration (Future)
- [ ] Evaluate if ORM improves maintainability for current scope
- [ ] If yes: Plan migration from raw SQL to SQLAlchemy
- [ ] Map models.py classes to SQLAlchemy models
- [ ] Convert database methods to use ORM

---

## Questions Answered (2025-12-22)

**Q: Is fund_name_mapping table actually needed?**
- A: Not in current pipeline. The table IS used by `populate_fund_mappings()` in src/standardize_fund_names.py, but that script is never called. Current pipeline uses src/apply_fund_mapping.py which updates transactions.mapped_fund_name directly. Options: keep as legacy backup, remove entirely, or consolidate both approaches.

**Q: What's the crossover between fund_ticker_mapping and mapping_status?**
- A: Different purposes:
  - `fund_ticker_mapping`: "How do I find price data for this fund?" (reference)
  - `mapping_status`: "When did I buy/sell this fund?" (analytics)
  - See DATABASE_SCHEMA.md for details

**Q: Is mapping_status documented with docstrings?**
- A: Partially. Created DATABASE_SCHEMA.md with full documentation. Code comments still needed.

---

## Recently Completed (2025-12-22)
- ✓ Added LU1033663649 (correct Fidelity Global Tech ticker)
- ✓ Added SUUS.L (iShares MSCI USA SRI) ticker mapping
- ✓ Added SMT.L (Scottish Mortgage) ticker mapping
- ✓ Created mapping_status table for transaction date tracking
- ✓ Downloaded 4,541+ price records for new tickers
- ✓ Created DATABASE_SCHEMA.md documentation
- ✓ Updated fund_rename_mapping.json with Fidelity mapping

---

## Notes
- Ensure all scripts are thoroughly tested before deployment
- Keep local SQLite backup while testing cloud migration
- Document all API keys and credentials securely
- Consider staging environment before production deployment
- Database schema is stable but has redundancy that should be cleaned up (see Section 4)