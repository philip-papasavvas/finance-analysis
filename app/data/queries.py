"""Database query functions for portfolio viewer."""

import json
import logging

import pandas as pd

from portfolio.core.database import TransactionDatabase
from app.data import sql

logger = logging.getLogger(__name__)


def get_all_funds_from_db():
    """Get all unique funds from the database with their mapped names (excluding excluded funds)."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute(sql.GET_ALL_FUNDS)
    funds = {}
    for row in cursor.fetchall():
        funds[row["fund_name"]] = row["display_name"]
    db.close()
    return funds


def get_fund_transactions(fund_name: str) -> pd.DataFrame:
    """Get transactions for a specific fund."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute(sql.GET_FUND_TRANSACTIONS, (fund_name,))

    rows = cursor.fetchall()
    db.close()

    if not rows:
        return pd.DataFrame()

    data = []
    for row in rows:
        # Use mapped name if available, otherwise original name
        display_name = row["mapped_fund_name"] if row["mapped_fund_name"] else row["fund_name"]

        data.append(
            {
                "Date": row["date"],
                "Platform": row["platform"],
                "Tax Wrapper": row["tax_wrapper"],
                "Fund Name": display_name,
                "Type": row["transaction_type"],
                "Units": row["units"],
                "Price (£)": row["price_per_unit"],
                "Value (£)": row["value"],
                "Currency": row["currency"],
            }
        )

    return pd.DataFrame(data)


def get_all_transactions() -> pd.DataFrame:
    """Get all transactions from the database."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute(sql.GET_ALL_TRANSACTIONS)

    rows = cursor.fetchall()
    db.close()

    if not rows:
        return pd.DataFrame()

    data = []
    for row in rows:
        data.append(
            {
                "Date": row["date"],
                "Platform": row["platform"],
                "Tax Wrapper": row["tax_wrapper"],
                "Fund Name": row["fund_name"],
                "Type": row["transaction_type"],
                "Units": row["units"],
                "Price (£)": row["price_per_unit"],
                "Value (£)": row["value"],
                "Currency": row["currency"],
            }
        )

    return pd.DataFrame(data)


def get_recent_transactions(limit: int = 10) -> pd.DataFrame:
    """Get the N most recent transactions with mapped fund names."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute(sql.GET_RECENT_TRANSACTIONS, (limit,))

    rows = cursor.fetchall()
    db.close()

    if not rows:
        return pd.DataFrame()

    data = []
    for row in rows:
        data.append(
            {
                "Date": row["date"],
                "Fund Name": row["fund_name"],
                "Type": row["transaction_type"],
                "Units": row["units"],
                "Value (£)": row["value"],
                "Platform": row["platform"],
                "Tax Wrapper": row["tax_wrapper"],
            }
        )

    return pd.DataFrame(data)


def get_fund_holdings() -> pd.DataFrame:
    """Get current holdings for each fund (units held, excluding zero holdings)."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute(sql.GET_FUND_HOLDINGS)

    rows = cursor.fetchall()
    db.close()

    if not rows:
        return pd.DataFrame()

    data = []
    for row in rows:
        data.append(
            {
                "Fund Name": row["fund_name"],
                "Units Held": row["units_held"],
                "Transactions": row["transaction_count"],
            }
        )

    return pd.DataFrame(data)


def get_standardized_name(original_name: str) -> str:
    """Get the standardized/mapped name for a fund from transactions table."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute(sql.GET_STANDARDIZED_NAME, (original_name,))
    result = cursor.fetchone()
    db.close()
    if result:
        return result["display_name"]
    return original_name


def get_all_price_tickers():
    """Get all available price tickers from the database."""
    db = TransactionDatabase("portfolio.db")
    tickers = db.get_all_price_tickers()
    db.close()
    return tickers


def get_ticker_info_dict():
    """Get information about all tickers as a dictionary (ticker -> fund_name)."""
    db = TransactionDatabase("portfolio.db")
    ticker_info = db.get_ticker_info()
    db.close()
    return {info["ticker"]: info["fund_name"] for info in ticker_info}


def get_price_history(ticker: str) -> pd.DataFrame:
    """Get price history for a specific ticker."""
    db = TransactionDatabase("portfolio.db")
    prices = db.get_price_history_by_ticker(ticker)
    db.close()

    if not prices:
        return pd.DataFrame()

    df = pd.DataFrame(prices)
    df["Date"] = pd.to_datetime(df["date"])
    df = df.rename(columns={"close_price": "Price"})
    return df[["Date", "Price", "ticker", "fund_name"]].sort_values("Date")


def get_transactions_for_ticker(ticker: str) -> pd.DataFrame:
    """Get buy/sell transactions for a specific ticker using fund_ticker_mapping."""
    db = TransactionDatabase("portfolio.db")
    transactions = db.get_transactions_for_ticker(ticker)
    db.close()

    if not transactions:
        return pd.DataFrame()

    data = []
    for row in transactions:
        data.append(
            {
                "Date": pd.to_datetime(row["date"]),
                "Type": row["transaction_type"],
                "Units": row["units"],
                "Price": row["price_per_unit"],
                "Value": row["value"],
                "Marker_Y": row["marker_y"],  # Y-position on chart (close price from that date)
            }
        )

    return pd.DataFrame(data)


def get_fund_mapping_status() -> pd.DataFrame:
    """Get mapping status for all funds with transactions.

    Returns DataFrame with columns:
    - fund_name: Original fund name
    - mapped_fund_name: Mapped fund name (if available)
    - transaction_count: Number of transactions
    - ticker: Mapped ticker (if available)
    - has_price_history: Boolean indicating if price history exists
    - vip: Boolean indicating if ticker is marked as VIP
    """
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()

    cursor.execute(sql.GET_FUND_MAPPING_STATUS)

    data = []
    for row in cursor.fetchall():
        fund_name = row["fund_name"]
        transaction_count = row["transaction_count"]
        mapped_fund_name = row["mapped_fund_name"] if row["mapped_fund_name"] else None

        # Get mapping for this fund
        mapping = db.get_ticker_for_fund(fund_name)
        ticker = mapping if mapping else None

        # Check if we have price history for this ticker
        has_price_history = False
        vip = False
        if ticker:
            cursor.execute(sql.GET_PRICE_HISTORY_COUNT, (ticker,))
            result = cursor.fetchone()
            has_price_history = result["count"] > 0 if result else False

            # Check VIP status
            cursor.execute(sql.GET_VIP_STATUS, (ticker,))
            vip_result = cursor.fetchone()
            vip = bool(vip_result["vip"]) if vip_result and vip_result["vip"] else False

        data.append(
            {
                "fund_name": fund_name,
                "mapped_fund_name": mapped_fund_name if mapped_fund_name else "—",
                "transaction_count": transaction_count,
                "ticker": ticker if ticker else "—",
                "has_price_history": has_price_history,
                "vip": vip,
            }
        )

    db.close()
    # Sort by VIP (descending) then by transaction count (descending)
    df = pd.DataFrame(data)
    df = df.sort_values(by=["vip", "transaction_count"], ascending=[False, False])
    return df


def get_gbp_usd_rate():
    """Get current GBP/USD exchange rate using yfinance."""
    import yfinance as yf

    try:
        # Fetch GBP/USD rate (inverted because we want USD to GBP)
        rate_ticker = yf.Ticker("GBPUSD=X")
        rate_data = rate_ticker.history(period="1d")
        if not rate_data.empty:
            gbp_usd = rate_data["Close"].iloc[-1]
            # We want USD to GBP, so invert
            usd_to_gbp = 1 / gbp_usd
            return usd_to_gbp
        else:
            logger.warning("Could not fetch GBP/USD rate, using default 0.74")
            return 0.74  # Fallback rate
    except Exception as e:
        logger.error(f"Error fetching exchange rate: {e}")
        return 0.74  # Fallback rate


def get_gbp_eur_rate():
    """Get current GBP/EUR exchange rate using yfinance."""
    import yfinance as yf

    try:
        # Fetch GBP/EUR rate (inverted because we want EUR to GBP)
        rate_ticker = yf.Ticker("GBPEUR=X")
        rate_data = rate_ticker.history(period="1d")
        if not rate_data.empty:
            gbp_eur = rate_data["Close"].iloc[-1]
            # We want EUR to GBP, so invert
            eur_to_gbp = 1 / gbp_eur
            return eur_to_gbp
        else:
            logger.warning("Could not fetch GBP/EUR rate, using default 0.83")
            return 0.83  # Fallback rate
    except Exception as e:
        logger.error(f"Error fetching EUR/GBP exchange rate: {e}")
        return 0.83  # Fallback rate


def get_portfolio_value_timeseries(
    include_benchmark: bool = True, benchmark_ticker: str = "VWRL.L"
) -> pd.DataFrame:
    """Calculate portfolio value for each date in price history.

    Args:
        include_benchmark: Whether to include benchmark returns
        benchmark_ticker: Ticker to use as benchmark (default VWRL.L)

    Returns DataFrame with columns:
    - Date: datetime
    - Value: total portfolio value in GBP
    - Benchmark_Price: benchmark price (if include_benchmark=True)

    Uses forward-fill for missing prices to handle gaps in price data.
    Converts LSE pence prices to pounds.
    """
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()

    # Get all transactions with tickers
    cursor.execute(sql.GET_ALL_TRANSACTIONS_WITH_TICKERS)
    transactions = cursor.fetchall()

    # Get all price history
    cursor.execute(sql.GET_ALL_PRICE_HISTORY)
    prices = cursor.fetchall()

    db.close()

    if not transactions or not prices:
        return pd.DataFrame()

    # Build transaction DataFrame
    tx_df = pd.DataFrame([dict(row) for row in transactions])
    tx_df["date"] = pd.to_datetime(tx_df["date"])

    # Build price DataFrame
    price_df = pd.DataFrame([dict(row) for row in prices])
    price_df["date"] = pd.to_datetime(price_df["date"])

    # Convert pence prices to pounds
    # yfinance returns some LSE tickers in GBP, others in pence
    # Vanguard ETFs are returned in GBP by yfinance
    # Most other .L tickers are returned in pence

    # Tickers known to be returned in GBP (not pence) by yfinance
    gbp_tickers = {
        "VWRL.L",
        "VUAG.L",
        "VUSA.L",
        "VUKE.L",
        "VERG.L",
        "VFEM.L",
        "VWRP.L",  # Vanguard only
    }

    lse_mask = price_df["ticker"].str.endswith(".L")
    isin_mask = (
        price_df["ticker"].str.startswith("GB00")
        | price_df["ticker"].str.startswith("IE00")
        | price_df["ticker"].str.startswith("LU")
    )

    # Exclude known GBP tickers from pence conversion
    not_gbp_ticker = ~price_df["ticker"].isin(gbp_tickers)

    # Apply threshold of 50 for pence-quoted tickers (£50+ is almost certainly pence)
    lse_high_price = lse_mask & not_gbp_ticker & (price_df["close_price"] > 50)
    isin_high_price = isin_mask & (price_df["close_price"] > 50)

    price_df.loc[lse_high_price, "close_price"] = price_df.loc[lse_high_price, "close_price"] / 100
    price_df.loc[isin_high_price, "close_price"] = (
        price_df.loc[isin_high_price, "close_price"] / 100
    )

    # Create a pivot table of prices: date x ticker
    price_pivot = price_df.pivot_table(
        index="date", columns="ticker", values="close_price", aggfunc="first"
    )

    # Forward-fill missing prices (use last known price when data is missing)
    price_pivot = price_pivot.ffill()

    # Filter out tickers with insufficient price history (less than 30 days)
    # This prevents discontinuities when sparse price data appears
    min_price_days = 30
    valid_tickers = [
        col for col in price_pivot.columns if price_pivot[col].notna().sum() >= min_price_days
    ]
    price_pivot = price_pivot[valid_tickers]

    # Get unique dates from price history
    all_dates = sorted(price_pivot.index.unique())

    # Calculate cumulative units held per ticker as of each date
    # Only include tickers that have sufficient price history
    tickers = [t for t in tx_df["ticker"].unique() if t in valid_tickers]

    # For each ticker, calculate cumulative units at each date
    cumulative_units = {}
    first_tx_dates = {}  # Track when each ticker was first purchased
    for ticker in tickers:
        ticker_tx = tx_df[tx_df["ticker"] == ticker].sort_values("date")
        # Calculate signed units (positive for BUY, negative for SELL)
        ticker_tx = ticker_tx.copy()
        ticker_tx["signed_units"] = ticker_tx.apply(
            lambda row: row["units"] if row["transaction_type"] == "BUY" else -row["units"], axis=1
        )
        ticker_tx["cumulative"] = ticker_tx["signed_units"].cumsum()

        # Create a series of cumulative units indexed by date
        cumulative_units[ticker] = ticker_tx.set_index("date")["cumulative"]

        # Track first transaction date for this ticker
        if not ticker_tx.empty:
            first_tx_dates[ticker] = ticker_tx["date"].min()

    # Calculate portfolio value at each date
    portfolio_values = []

    for date in all_dates:
        total_value = 0.0

        for ticker in tickers:
            # Skip if this is before the first transaction for this ticker
            if ticker in first_tx_dates and date < first_tx_dates[ticker]:
                continue

            # Get units held as of this date (latest cumulative up to this date)
            if ticker in cumulative_units:
                cum_series = cumulative_units[ticker]
                # Get all cumulative values up to and including this date
                valid_entries = cum_series[cum_series.index <= date]
                if len(valid_entries) > 0:
                    units = valid_entries.iloc[-1]
                else:
                    units = 0.0
            else:
                units = 0.0

            # Skip if no units held
            if units <= 0:
                continue

            # Get price for this ticker on this date (now with forward-fill)
            if ticker in price_pivot.columns and date in price_pivot.index:
                price = price_pivot.loc[date, ticker]
                if pd.notna(price):
                    total_value += units * price

        portfolio_values.append({"Date": date, "Value": total_value})

    result_df = pd.DataFrame(portfolio_values)
    # Filter out dates before first transaction
    if not tx_df.empty:
        first_tx_date = tx_df["date"].min()
        result_df = result_df[result_df["Date"] >= first_tx_date]

    # Filter out rows where value is 0 (no valid price data yet)
    result_df = result_df[result_df["Value"] > 0]

    # Add benchmark data if requested
    if include_benchmark and benchmark_ticker in price_pivot.columns:
        # Get benchmark prices and add to result
        benchmark_prices = price_pivot[benchmark_ticker].reset_index()
        benchmark_prices.columns = ["Date", "Benchmark_Price"]
        result_df = result_df.merge(benchmark_prices, on="Date", how="left")
        # Forward fill any missing benchmark prices
        result_df["Benchmark_Price"] = result_df["Benchmark_Price"].ffill()

    return result_df


def get_current_holdings_vip():
    """Get current holdings from JSON file for VIP funds only, using mapped fund names.
    Converts USD and EUR prices to GBP for consistency.
    """
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()

    # Load holdings from JSON file (new format: grouped by ticker)
    holdings_file = "data/current_holdings.json"
    try:
        with open(holdings_file, "r") as f:
            holdings_by_ticker = json.load(f)
    except FileNotFoundError:
        logger.error(f"Holdings file not found: {holdings_file}")
        return pd.DataFrame()

    # Get current USD to GBP exchange rate
    usd_to_gbp = get_gbp_usd_rate()
    logger.info(f"Using USD to GBP exchange rate: {usd_to_gbp:.4f}")

    # Get current EUR to GBP exchange rate
    eur_to_gbp = get_gbp_eur_rate()
    logger.info(f"Using EUR to GBP exchange rate: {eur_to_gbp:.4f}")

    # Define which tickers are in USD and EUR
    usd_tickers = {"BRK-B", "NVDA", "AMZN"}
    eur_tickers = {"MWOT.DE"}

    # Get VIP ticker info with mapped names and prices
    cursor.execute(sql.GET_VIP_TICKER_INFO)

    ticker_info = {}
    for row in cursor.fetchall():
        original_price = row["latest_price"] if row["latest_price"] else 0
        ticker = row["ticker"]

        # Convert USD and EUR prices to GBP
        if ticker in usd_tickers:
            gbp_price = original_price * usd_to_gbp
            currency = "USD"
        elif ticker in eur_tickers:
            gbp_price = original_price * eur_to_gbp
            currency = "EUR"
        else:
            gbp_price = original_price
            currency = "GBP"

        ticker_info[ticker] = {
            "mapped_name": row["mapped_name"] if row["mapped_name"] else "Unknown",
            "price": gbp_price,  # Always in GBP now
            "original_price": original_price,
            "currency": currency,
            "price_date": row["price_date"],
        }

    # Process holdings from new JSON format (grouped by ticker)
    data = []
    for ticker, ticker_data in holdings_by_ticker.items():
        # Only include VIP funds
        if ticker not in ticker_info:
            continue

        info = ticker_info[ticker]

        # Process each holding for this ticker
        for holding in ticker_data.get("holdings", []):
            units = holding.get("units", 0)
            value = units * info["price"]  # Value is now always in GBP

            data.append(
                {
                    "fund_name": info["mapped_name"],  # Use mapped name from database
                    "tax_wrapper": holding.get("tax_wrapper"),
                    "platform": holding.get("platform"),
                    "ticker": ticker,
                    "units": units,
                    "price": info["price"],  # GBP price
                    "original_price": info["original_price"],  # Original currency price
                    "currency": info["currency"],
                    "value": value,  # Value in GBP
                    "price_date": info["price_date"],
                }
            )

    db.close()
    return pd.DataFrame(data)


def get_aggregated_holdings():
    """Get aggregated holdings by ticker with cost basis and breakdown details.

    Returns a list of dictionaries, each containing:
    - ticker: The ticker symbol
    - fund_name: Display name of the fund
    - total_units: Aggregated units across all wrappers/platforms
    - price: Latest price in GBP
    - total_value: total_units * price
    - cost_basis: Total cost of acquisition
    - avg_cost_per_unit: Average cost per unit
    - gain_loss: total_value - cost_basis
    - gain_loss_pct: Percentage gain/loss
    - currency: Original currency of the ticker
    - price_date: Date of the latest price
    - holdings: List of individual holdings (for breakdown view)
    """
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()

    # Load holdings from JSON file
    holdings_file = "data/current_holdings.json"
    try:
        with open(holdings_file, "r") as f:
            holdings_by_ticker = json.load(f)
    except FileNotFoundError:
        logger.error(f"Holdings file not found: {holdings_file}")
        return []

    # Get exchange rates
    usd_to_gbp = get_gbp_usd_rate()
    eur_to_gbp = get_gbp_eur_rate()
    logger.info(f"Using USD to GBP: {usd_to_gbp:.4f}, EUR to GBP: {eur_to_gbp:.4f}")

    # Define currency tickers
    usd_tickers = {"BRK-B", "NVDA", "AMZN"}
    eur_tickers = {"MWOT.DE"}

    # Get latest prices for all tickers
    cursor.execute(sql.GET_LATEST_PRICES)
    price_info = {}
    for row in cursor.fetchall():
        ticker = row["ticker"]
        original_price = row["latest_price"] if row["latest_price"] else 0

        # Convert to GBP
        if ticker in usd_tickers:
            gbp_price = original_price * usd_to_gbp
            currency = "USD"
        elif ticker in eur_tickers:
            gbp_price = original_price * eur_to_gbp
            currency = "EUR"
        else:
            gbp_price = original_price
            currency = "GBP"

        price_info[ticker] = {
            "fund_name": row["mapped_name"] if row["mapped_name"] else row["fund_name"],
            "price": gbp_price,
            "original_price": original_price,
            "currency": currency,
            "price_date": row["price_date"],
        }

    # Get cost basis for all tickers (aggregated)
    cursor.execute(sql.GET_COST_BASIS_BY_TICKER)
    cost_basis_info = {}
    for row in cursor.fetchall():
        ticker = row["ticker"]
        total_units_bought = row["total_units_bought"] or 0
        total_cost = row["total_cost"] or 0
        total_units_sold = row["total_units_sold"] or 0
        total_proceeds = row["total_proceeds"] or 0

        # Calculate average cost per unit (using average cost method)
        avg_cost = total_cost / total_units_bought if total_units_bought > 0 else 0

        # Remaining cost basis = total_cost - (avg_cost * units_sold)
        remaining_cost_basis = total_cost - (avg_cost * total_units_sold)

        cost_basis_info[ticker] = {
            "total_units_bought": total_units_bought,
            "total_cost": total_cost,
            "total_units_sold": total_units_sold,
            "total_proceeds": total_proceeds,
            "avg_cost_per_unit": avg_cost,
            "remaining_cost_basis": remaining_cost_basis,
        }

    # Get granular cost basis by ticker/wrapper/platform
    cursor.execute(sql.GET_COST_BASIS_BY_TICKER_WRAPPER_PLATFORM)
    granular_cost_basis = {}
    for row in cursor.fetchall():
        ticker = row["ticker"]
        wrapper = row["tax_wrapper"]
        platform = row["platform"]
        total_units_bought = row["total_units_bought"] or 0
        total_cost = row["total_cost"] or 0
        total_units_sold = row["total_units_sold"] or 0

        # Calculate average cost per unit for this wrapper/platform
        avg_cost = total_cost / total_units_bought if total_units_bought > 0 else 0

        # Net units from transactions
        net_units = total_units_bought - total_units_sold

        # Key for lookup
        key = (ticker, wrapper, platform)
        granular_cost_basis[key] = {
            "total_units_bought": total_units_bought,
            "total_cost": total_cost,
            "total_units_sold": total_units_sold,
            "avg_cost_per_unit": avg_cost,
            "net_units": net_units,
        }

    db.close()

    # Build aggregated holdings
    aggregated = []
    for ticker, ticker_data in holdings_by_ticker.items():
        holdings_list = ticker_data.get("holdings", [])
        if not holdings_list:
            continue

        # Aggregate units
        total_units = sum(h.get("units", 0) for h in holdings_list)

        # Get price info (use JSON fund_name as fallback)
        info = price_info.get(ticker, {})
        price = info.get("price", 0)
        fund_name = info.get("fund_name") or ticker_data.get("fund_name", ticker)
        currency = info.get("currency", "GBP")
        price_date = info.get("price_date")

        # Calculate total value
        total_value = total_units * price

        # Get cost basis info
        cb_info = cost_basis_info.get(ticker, {})
        avg_cost_per_unit = cb_info.get("avg_cost_per_unit", 0)

        # Calculate cost basis for current holdings
        cost_basis = total_units * avg_cost_per_unit

        # Calculate gain/loss
        gain_loss = total_value - cost_basis if cost_basis > 0 else 0
        gain_loss_pct = (gain_loss / cost_basis * 100) if cost_basis > 0 else 0

        # Build holdings breakdown with values and granular cost basis
        holdings_breakdown = []
        for h in holdings_list:
            units = h.get("units", 0)
            value = units * price
            wrapper = h.get("tax_wrapper")
            platform = h.get("platform")

            # Get granular cost basis for this wrapper/platform
            key = (ticker, wrapper, platform)
            gcb = granular_cost_basis.get(key, {})
            h_avg_cost = gcb.get("avg_cost_per_unit", avg_cost_per_unit)  # Fallback to ticker avg

            # Calculate cost and gain/loss for this holding
            h_cost = units * h_avg_cost
            h_gain = value - h_cost
            h_gain_pct = (h_gain / h_cost * 100) if h_cost > 0 else 0

            holdings_breakdown.append(
                {
                    "tax_wrapper": wrapper,
                    "platform": platform,
                    "units": units,
                    "value": value,
                    "cost": h_cost,
                    "gain_loss": h_gain,
                    "gain_loss_pct": h_gain_pct,
                    "avg_cost_per_unit": h_avg_cost,
                }
            )

        aggregated.append(
            {
                "ticker": ticker,
                "fund_name": fund_name,
                "total_units": total_units,
                "price": price,
                "total_value": total_value,
                "cost_basis": cost_basis,
                "avg_cost_per_unit": avg_cost_per_unit,
                "gain_loss": gain_loss,
                "gain_loss_pct": gain_loss_pct,
                "currency": currency,
                "price_date": price_date,
                "holdings": holdings_breakdown,
            }
        )

    # Sort by total value descending
    aggregated.sort(key=lambda x: x["total_value"], reverse=True)

    return aggregated
