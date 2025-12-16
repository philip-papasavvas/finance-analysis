# Portfolio Viewer - To-Do List

## 1. Price Data Management Script
### 1.1 Create Dynamic Price Update Script
- [ ] Design script that accepts minimum and maximum date parameters
- [ ] Implement logic to detect missing price data within date range
- [ ] Fetch missing price data from yfinance for all tickers/ISINs
- [ ] Handle API rate limiting and retries
- [ ] Insert/update missing data into price_history table
- [ ] Add logging to track which tickers were updated and date ranges

### 1.2 Implement One-Off Backfill Capability
- [ ] Create separate function for historical data backfill
- [ ] Allow bulk import of historical prices for date ranges
- [ ] Add progress indicators for long-running operations
- [ ] Validate data before insertion (no duplicates, valid prices)
- [ ] Generate report of successfully imported vs failed tickers

### 1.3 Script Entry Point
- [ ] Create CLI interface (e.g., `python scripts/update_prices.py --min-date 2020-01-01 --max-date 2025-12-31`)
- [ ] Add dry-run mode to preview changes without committing
- [ ] Support updating specific tickers vs all tickers
- [ ] Add scheduling support (cron job ready)

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

## Notes
- Ensure all scripts are thoroughly tested before deployment
- Keep local SQLite backup while testing cloud migration
- Document all API keys and credentials securely
- Consider staging environment before production deployment