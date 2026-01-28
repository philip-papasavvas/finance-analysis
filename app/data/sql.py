"""SQL queries for portfolio viewer."""

# ============================================================================
# Fund Queries
# ============================================================================

GET_ALL_FUNDS = """
    SELECT DISTINCT fund_name, COALESCE(mapped_fund_name, fund_name) as display_name
    FROM transactions
    WHERE excluded = 0
    ORDER BY COALESCE(mapped_fund_name, fund_name)
"""

GET_FUND_TRANSACTIONS = """
    SELECT
        date,
        platform,
        tax_wrapper,
        fund_name,
        mapped_fund_name,
        transaction_type,
        units,
        price_per_unit,
        value,
        currency
    FROM transactions
    WHERE fund_name = ? AND excluded = 0
    ORDER BY date
"""

GET_ALL_TRANSACTIONS = """
    SELECT
        date,
        platform,
        tax_wrapper,
        fund_name,
        transaction_type,
        units,
        price_per_unit,
        value,
        currency
    FROM transactions
    ORDER BY date DESC
"""

GET_RECENT_TRANSACTIONS = """
    SELECT
        date,
        platform,
        tax_wrapper,
        COALESCE(mapped_fund_name, fund_name) as fund_name,
        transaction_type,
        units,
        value
    FROM transactions
    WHERE excluded = 0
    ORDER BY date DESC
    LIMIT ?
"""

GET_FUND_HOLDINGS = """
    SELECT
        fund_name,
        SUM(CASE WHEN transaction_type = 'BUY' THEN units ELSE -units END) as units_held,
        COUNT(*) as transaction_count
    FROM transactions
    WHERE excluded = 0
    GROUP BY fund_name
    HAVING units_held > 0
    ORDER BY units_held DESC
"""

GET_STANDARDIZED_NAME = """
    SELECT COALESCE(mapped_fund_name, fund_name) as display_name
    FROM transactions
    WHERE fund_name = ?
    LIMIT 1
"""

# ============================================================================
# Mapping Queries
# ============================================================================

GET_FUND_MAPPING_STATUS = """
    SELECT fund_name, COUNT(*) as transaction_count,
           MAX(COALESCE(mapped_fund_name, '')) as mapped_fund_name
    FROM transactions
    WHERE excluded = 0
    GROUP BY fund_name
    ORDER BY transaction_count DESC
"""

GET_PRICE_HISTORY_COUNT = """
    SELECT COUNT(*) as count FROM price_history WHERE ticker = ?
"""

GET_VIP_STATUS = """
    SELECT vip FROM fund_ticker_mapping WHERE ticker = ? LIMIT 1
"""

# ============================================================================
# VIP Holdings Queries
# ============================================================================

GET_VIP_TICKER_INFO = """
    SELECT DISTINCT
        ftm.ticker,
        ftm.vip,
        COALESCE(
            (SELECT COALESCE(mapped_fund_name, fund_name) FROM transactions WHERE fund_name = ftm.fund_name LIMIT 1),
            ftm.fund_name
        ) as mapped_name,
        (SELECT close_price FROM price_history WHERE ticker = ftm.ticker ORDER BY date DESC LIMIT 1) as latest_price,
        (SELECT date FROM price_history WHERE ticker = ftm.ticker ORDER BY date DESC LIMIT 1) as price_date
    FROM fund_ticker_mapping ftm
    WHERE ftm.vip = 1
"""

# ============================================================================
# Funds List Queries
# ============================================================================

GET_FUNDS_WITH_COUNTS = """
    SELECT COALESCE(mapped_fund_name, fund_name) as display_name, COUNT(*) as tx_count
    FROM transactions
    WHERE excluded = 0
    GROUP BY COALESCE(mapped_fund_name, fund_name)
    ORDER BY COALESCE(mapped_fund_name, fund_name)
"""

# ============================================================================
# Portfolio Valuation Queries
# ============================================================================

GET_ALL_TRANSACTIONS_WITH_TICKERS = """
    SELECT
        t.date,
        t.transaction_type,
        t.units,
        ftm.ticker,
        t.platform,
        t.tax_wrapper
    FROM transactions t
    INNER JOIN fund_ticker_mapping ftm ON t.fund_name = ftm.fund_name
    WHERE t.excluded = 0
      AND t.transaction_type IN ('BUY', 'SELL')
      AND t.fund_name NOT LIKE '%Cash%'
      AND ftm.ticker != 'GB00BLPK7110'
    ORDER BY t.date
"""

GET_ALL_PRICE_HISTORY = """
    SELECT date, ticker, close_price
    FROM price_history
    ORDER BY date, ticker
"""

GET_UNIQUE_PRICE_DATES = """
    SELECT DISTINCT date
    FROM price_history
    ORDER BY date
"""

# ============================================================================
# Cost Basis Queries
# ============================================================================

GET_COST_BASIS_BY_TICKER = """
    SELECT
        ftm.ticker,
        SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.units ELSE 0 END) as total_units_bought,
        SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.value ELSE 0 END) as total_cost,
        SUM(CASE WHEN t.transaction_type = 'SELL' THEN t.units ELSE 0 END) as total_units_sold,
        SUM(CASE WHEN t.transaction_type = 'SELL' THEN t.value ELSE 0 END) as total_proceeds
    FROM fund_ticker_mapping ftm
    LEFT JOIN transactions t ON t.fund_name = ftm.fund_name
        AND t.excluded = 0
        AND t.transaction_type IN ('BUY', 'SELL')
    GROUP BY ftm.ticker
"""

GET_COST_BASIS_BY_TICKER_WRAPPER_PLATFORM = """
    SELECT
        ftm.ticker,
        t.tax_wrapper,
        t.platform,
        SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.units ELSE 0 END) as total_units_bought,
        SUM(CASE WHEN t.transaction_type = 'BUY' THEN t.value ELSE 0 END) as total_cost,
        SUM(CASE WHEN t.transaction_type = 'SELL' THEN t.units ELSE 0 END) as total_units_sold,
        SUM(CASE WHEN t.transaction_type = 'SELL' THEN t.value ELSE 0 END) as total_proceeds
    FROM fund_ticker_mapping ftm
    LEFT JOIN transactions t ON t.fund_name = ftm.fund_name
        AND t.excluded = 0
        AND t.transaction_type IN ('BUY', 'SELL')
    WHERE t.tax_wrapper IS NOT NULL AND t.platform IS NOT NULL
    GROUP BY ftm.ticker, t.tax_wrapper, t.platform
"""

GET_LATEST_PRICES = """
    SELECT
        ftm.ticker,
        ftm.fund_name,
        COALESCE(ftm.mapped_fund_name, ftm.fund_name) as mapped_name,
        ph.close_price as latest_price,
        ph.date as price_date
    FROM fund_ticker_mapping ftm
    LEFT JOIN (
        SELECT ticker, close_price, date,
               ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) as rn
        FROM price_history
    ) ph ON ph.ticker = ftm.ticker AND ph.rn = 1
"""
