# Portfolio Viewer - To-Do List

## 1. Core Holdings Price & Transaction Verification
### 1.1 Identify Important Holdings
- [ ] Define criteria for "important" holdings (e.g., > £X value, actively traded, etc.)
- [ ] Generate list of priority tickers/ISINs
- [ ] Create mapping of holdings to tickers/ISINs for easy reference

### 1.2 Verify Data Completeness
- [ ] Audit which important holdings have complete price history
- [ ] Audit which important holdings have complete transaction records
- [ ] Identify gaps in price data (missing date ranges)
- [ ] Identify gaps in transaction data
- [ ] Create coverage report showing completeness %

### 1.3 Priority Tickers/ISINs List
- [ ] Document the complete list of priority tickers/ISINs with status
- [ ] Create table showing:
  - Ticker/ISIN
  - Fund Name
  - Has Price History (Yes/No, date range if yes)
  - Has Transactions (Yes/No, count)
  - Data Completeness %
  - Status (Complete / Needs Update / Incomplete)

---

## 2. Cloud Deployment & Online Hosting
### 2.1 Infrastructure Setup
- [ ] Choose cloud provider (AWS, Google Cloud, Azure, Heroku, etc.)
- [ ] Set up cloud database (PostgreSQL, MySQL, or cloud SQLite equivalent)
- [ ] Migrate SQLite database to cloud database
- [ ] Set up secure database connection strings
- [ ] Test data integrity after migration

### 2.2 Application Deployment
- [ ] Deploy Streamlit app to cloud (e.g., Streamlit Cloud, Heroku, Docker container)
- [ ] Configure environment variables for cloud database
- [ ] Test all tabs and functionality in cloud environment
- [ ] Set up automated deployments (CI/CD pipeline)

### 2.3 Authentication & Authorization
- [ ] Implement user authentication (login system)
- [ ] Set up user roles/permissions if multi-user access needed
- [ ] Secure API endpoints and database access
- [ ] Add rate limiting to prevent abuse
- [ ] Implement password management (reset, change, etc.)

### 2.4 Security Hardening
- [ ] Enable HTTPS/SSL certificates
- [ ] Set up firewall rules and network isolation
- [ ] Configure database access controls
- [ ] Enable audit logging for data access
- [ ] Set up automated backups
- [ ] Document security policies

### 2.5 Monitoring & Maintenance
- [ ] Set up application monitoring (uptime, errors, performance)
- [ ] Configure alerts for critical issues
- [ ] Set up database backup schedule (daily minimum)
- [ ] Document disaster recovery procedures
- [ ] Plan for regular security updates

### 2.6 Documentation
- [ ] Create deployment guide
- [ ] Document cloud setup steps
- [ ] Create user guide for accessing cloud version
- [ ] Document backup/restore procedures
- [ ] Create troubleshooting guide

---

## Priority Order
1. **High Priority:** Core Holdings Verification (Section 1)
2. **Medium Priority:** Cloud Deployment (Section 2)

---

---

## 3. Database Schema Cleanup & Documentation ✓ COMPLETED
### 3.1 Remove fund_name_mapping Table ✓
- [x] Removed table creation from database.py
- [x] Removed related methods (add_fund_mapping, get_standardized_name, etc.)
- [x] Deprecated populate_fund_mappings() in standardize_fund_names.py
- [x] Updated DATABASE_SCHEMA.md to document removal

### 3.2 Clean Up mapping_status Table ✓
- [x] Deleted FDTEC entry (replaced with LU1033663649)
- [x] Removed FDTEC from migrate_ticker_mappings.py
- [x] Cleaned up download_ticker_data.py

### 3.3 Add Database Documentation ✓
- [x] Created DATABASE_SCHEMA.md with full table documentation
- [x] Added inline docstrings to create_tables() method
- [x] Documented fund_ticker_mapping vs mapping_status distinction

### 3.4 Add Data Validation Script ✓
- [x] Created src/validate_database.py
- [x] Checks for orphaned funds, duplicate prices, missing data
- [x] Generates validation report with exit codes

### 3.5 Consider SQLAlchemy ORM Migration (Future)
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
- ✓ **Price Data Management Script** - Created scripts/update_prices.py with CLI interface
  - Date range parameters (--min-date, --max-date)
  - Backfill mode for historical imports
  - Dry-run mode to preview changes
  - Ticker selection and rate limiting
- ✓ **Database Schema Cleanup** - Removed unused fund_name_mapping table
- ✓ **Validation Script** - Created src/validate_database.py
- ✓ Fixed Amundi ticker (MWOT.DE) and backfilled price data
- ✓ Cleaned up FDTEC entries (replaced with LU1033663649)
- ✓ Added LU1033663649, SUUS.L, SMT.L ticker mappings
- ✓ Created DATABASE_SCHEMA.md and CLAUDE.md documentation
- ✓ Updated README.md with comprehensive project structure

---

## Notes
- Ensure all scripts are thoroughly tested before deployment
- Keep local SQLite backup while testing cloud migration
- Document all API keys and credentials securely
- Consider staging environment before production deployment
- Database schema is stable but has redundancy that should be cleaned up (see Section 4)