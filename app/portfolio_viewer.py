"""
Streamlit app for viewing portfolio transactions with interactive fund selection.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Add parent directory to path so we can import src
# sys.path adjustment no longer needed - using proper package structure

from portfolio.core.database import TransactionDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_all_funds_from_db():
    """Get all unique funds from the database with their mapped names (excluding excluded funds)."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT DISTINCT fund_name, COALESCE(mapped_fund_name, fund_name) as display_name
        FROM transactions
        WHERE excluded = 0
        ORDER BY COALESCE(mapped_fund_name, fund_name)
    """)
    funds = {}
    for row in cursor.fetchall():
        funds[row["fund_name"]] = row["display_name"]
    db.close()
    return funds


def get_fund_transactions(fund_name: str) -> pd.DataFrame:
    """Get transactions for a specific fund."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute("""
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
    """, (fund_name,))

    rows = cursor.fetchall()
    db.close()

    if not rows:
        return pd.DataFrame()

    data = []
    for row in rows:
        # Use mapped name if available, otherwise original name
        display_name = row["mapped_fund_name"] if row["mapped_fund_name"] else row["fund_name"]

        data.append({
            "Date": row["date"],
            "Platform": row["platform"],
            "Tax Wrapper": row["tax_wrapper"],
            "Fund Name": display_name,
            "Type": row["transaction_type"],
            "Units": row["units"],
            "Price (£)": row["price_per_unit"],
            "Value (£)": row["value"],
            "Currency": row["currency"],
        })

    return pd.DataFrame(data)


def get_all_transactions() -> pd.DataFrame:
    """Get all transactions from the database."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute("""
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
    """)

    rows = cursor.fetchall()
    db.close()

    if not rows:
        return pd.DataFrame()

    data = []
    for row in rows:
        data.append({
            "Date": row["date"],
            "Platform": row["platform"],
            "Tax Wrapper": row["tax_wrapper"],
            "Fund Name": row["fund_name"],
            "Type": row["transaction_type"],
            "Units": row["units"],
            "Price (£)": row["price_per_unit"],
            "Value (£)": row["value"],
            "Currency": row["currency"],
        })

    return pd.DataFrame(data)


def get_fund_holdings() -> pd.DataFrame:
    """Get current holdings for each fund (units held, excluding zero holdings)."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT
            fund_name,
            SUM(CASE WHEN transaction_type = 'BUY' THEN units ELSE -units END) as units_held,
            COUNT(*) as transaction_count
        FROM transactions
        WHERE excluded = 0
        GROUP BY fund_name
        HAVING units_held > 0
        ORDER BY units_held DESC
    """)

    rows = cursor.fetchall()
    db.close()

    if not rows:
        return pd.DataFrame()

    data = []
    for row in rows:
        data.append({
            "Fund Name": row["fund_name"],
            "Units Held": row["units_held"],
            "Transactions": row["transaction_count"],
        })

    return pd.DataFrame(data)


def get_standardized_name(original_name: str) -> str:
    """Get the standardized/mapped name for a fund from transactions table."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT COALESCE(mapped_fund_name, fund_name) as display_name
        FROM transactions
        WHERE fund_name = ?
        LIMIT 1
    """, (original_name,))
    result = cursor.fetchone()
    db.close()
    if result:
        return result["display_name"]
    return original_name


def create_timeline_chart(df: pd.DataFrame, fund_name: str) -> go.Figure:
    """Create a bar chart of buy/sell transactions with positive/negative bars."""
    if df.empty:
        return None

    # Convert date to datetime
    df_chart = df.copy()
    df_chart["Date"] = pd.to_datetime(df_chart["Date"])
    df_chart = df_chart.sort_values("Date")

    # Create bar values (positive for buys, negative for sells)
    df_chart["Bar Value"] = df_chart.apply(
        lambda row: row["Units"] if row["Type"] == "BUY" else -row["Units"],
        axis=1
    )

    # Determine colors (green for buys, red for sells)
    colors = ["green" if val > 0 else "red" for val in df_chart["Bar Value"]]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df_chart["Date"],
        y=df_chart["Bar Value"],
        marker=dict(color=colors),
        name="Transactions",
        hovertemplate="<b>%{customdata}</b><br>Date: %{x|%Y-%m-%d}<br>Units: %{y:.2f}<extra></extra>",
        customdata=df_chart["Type"],
    ))

    # Add a horizontal line at y=0
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    # Update layout
    fig.update_layout(
        title=f"Buy/Sell Transactions - {fund_name}",
        xaxis_title="Date",
        yaxis_title="Units (Green = Buy, Red = Sell)",
        hovermode="x unified",
        height=400,
        template="plotly_white",
        showlegend=False,
    )

    return fig


def create_cumulative_units_chart(df: pd.DataFrame, fund_name: str) -> go.Figure:
    """Create a chart showing cumulative units over time."""
    if df.empty:
        return None

    # Convert date to datetime
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    # Calculate cumulative units (buys are positive, sells are negative)
    df["Cumulative Units"] = df["Units"].where(df["Type"] == "BUY", -df["Units"]).cumsum()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Cumulative Units"],
        fill="tozeroy",
        name="Cumulative Units",
        line=dict(color="blue", width=2),
        hovertemplate="<b>Cumulative Units</b><br>Date: %{x|%Y-%m-%d}<br>Units: %{y:.2f}<extra></extra>",
    ))

    fig.update_layout(
        title=f"Cumulative Units Over Time - {fund_name}",
        xaxis_title="Date",
        yaxis_title="Units Held",
        hovermode="x unified",
        height=400,
        template="plotly_white",
    )

    return fig


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
    return {info['ticker']: info['fund_name'] for info in ticker_info}


def get_price_history(ticker: str) -> pd.DataFrame:
    """Get price history for a specific ticker."""
    db = TransactionDatabase("portfolio.db")
    prices = db.get_price_history_by_ticker(ticker)
    db.close()

    if not prices:
        return pd.DataFrame()

    df = pd.DataFrame(prices)
    df['Date'] = pd.to_datetime(df['date'])
    df = df.rename(columns={'close_price': 'Price'})
    return df[['Date', 'Price', 'ticker', 'fund_name']].sort_values('Date')


def get_transactions_for_ticker(ticker: str) -> pd.DataFrame:
    """Get buy/sell transactions for a specific ticker using fund_ticker_mapping."""
    db = TransactionDatabase("portfolio.db")
    transactions = db.get_transactions_for_ticker(ticker)
    db.close()

    if not transactions:
        return pd.DataFrame()

    data = []
    for row in transactions:
        data.append({
            "Date": pd.to_datetime(row["date"]),
            "Type": row["transaction_type"],
            "Units": row["units"],
            "Price": row["price_per_unit"],
            "Value": row["value"],
            "Marker_Y": row["marker_y"],  # Y-position on chart (close price from that date)
        })

    return pd.DataFrame(data)


def create_price_chart(df: pd.DataFrame, ticker: str, fund_name: str, transactions_df: pd.DataFrame = None) -> go.Figure:
    """Create a line chart for price history with optional buy/sell transaction markers."""
    if df.empty:
        return None

    # Determine currency symbol based on ticker
    ticker_currency_map = {
        'BRK-B': '$',
        'EMIM.L': 'p',
        'GB00B2PLJD73': '£',
        'GB00BD6PG787': '£',
        'GB00BF0TZG22': 'p',
        'LU1033663649': '£',
        'MWOT.DE': '€',
        'NVDA': '$',
        'VERG.L': '£',
        'VUAG.L': '£',
        'VWRP.L': '£'
    }
    currency_symbol = ticker_currency_map.get(ticker, '£')

    fig = go.Figure()

    # Price line
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Price"],
        fill="tozeroy",
        name="Price",
        line=dict(color="green", width=2),
        hovertemplate=f"<b>Price</b><br>Date: %{{x|%Y-%m-%d}}<br>Price: {currency_symbol}%{{y:.2f}}<extra></extra>",
    ))

    # Add buy/sell markers if transactions data provided
    if transactions_df is not None and not transactions_df.empty:
        # Buy markers (dark green circles)
        buy_df = transactions_df[transactions_df["Type"] == "BUY"]
        if not buy_df.empty:
            fig.add_trace(go.Scatter(
                x=buy_df["Date"],
                y=buy_df["Marker_Y"],
                mode="markers",
                name="BUY",
                marker=dict(
                    color="darkgreen",
                    size=10,
                    symbol="circle",
                    line=dict(color="white", width=1)
                ),
                hovertemplate=(
                    "<b>BUY</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Units: %{customdata[0]:.2f}<br>"
                    "Price: £%{customdata[1]:.2f}<br>"
                    "Value: £%{customdata[2]:,.2f}"
                    "<extra></extra>"
                ),
                customdata=buy_df[["Units", "Price", "Value"]].values
            ))

        # Sell markers (dark red circles)
        sell_df = transactions_df[transactions_df["Type"] == "SELL"]
        if not sell_df.empty:
            fig.add_trace(go.Scatter(
                x=sell_df["Date"],
                y=sell_df["Marker_Y"],
                mode="markers",
                name="SELL",
                marker=dict(
                    color="darkred",
                    size=10,
                    symbol="circle",
                    line=dict(color="white", width=1)
                ),
                hovertemplate=(
                    "<b>SELL</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Units: %{customdata[0]:.2f}<br>"
                    "Price: £%{customdata[1]:.2f}<br>"
                    "Value: £%{customdata[2]:,.2f}"
                    "<extra></extra>"
                ),
                customdata=sell_df[["Units", "Price", "Value"]].values
            ))

    fig.update_layout(
        title=f"Price History - {fund_name} ({ticker})",
        xaxis_title="Date",
        yaxis_title="Price (£)",
        hovermode="closest",
        height=500,
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    return fig


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

    # Get all funds with transaction counts and mapped names
    cursor.execute("""
        SELECT fund_name, COUNT(*) as transaction_count,
               MAX(COALESCE(mapped_fund_name, '')) as mapped_fund_name
        FROM transactions
        WHERE excluded = 0
        GROUP BY fund_name
        ORDER BY transaction_count DESC
    """)

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
            cursor.execute("""
                SELECT COUNT(*) as count FROM price_history WHERE ticker = ?
            """, (ticker,))
            result = cursor.fetchone()
            has_price_history = result["count"] > 0 if result else False

            # Check VIP status
            cursor.execute("""
                SELECT vip FROM fund_ticker_mapping WHERE ticker = ? LIMIT 1
            """, (ticker,))
            vip_result = cursor.fetchone()
            vip = bool(vip_result["vip"]) if vip_result and vip_result["vip"] else False

        data.append({
            "fund_name": fund_name,
            "mapped_fund_name": mapped_fund_name if mapped_fund_name else "—",
            "transaction_count": transaction_count,
            "ticker": ticker if ticker else "—",
            "has_price_history": has_price_history,
            "vip": vip
        })

    db.close()
    # Sort by VIP (descending) then by transaction count (descending)
    df = pd.DataFrame(data)
    df = df.sort_values(by=["vip", "transaction_count"], ascending=[False, False])
    return df


def get_current_holdings_vip():
    """Get current holdings from JSON file for VIP funds only, using mapped fund names."""
    import json

    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()

    # Load holdings from JSON file (new format: grouped by ticker)
    holdings_file = 'data/current_holdings.json'
    try:
        with open(holdings_file, 'r') as f:
            holdings_by_ticker = json.load(f)
    except FileNotFoundError:
        logger.error(f"Holdings file not found: {holdings_file}")
        return pd.DataFrame()

    # Get VIP ticker info with mapped names and prices
    cursor.execute("""
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
    """)

    ticker_info = {}
    for row in cursor.fetchall():
        ticker_info[row["ticker"]] = {
            'mapped_name': row["mapped_name"] if row["mapped_name"] else "Unknown",
            'price': row["latest_price"] if row["latest_price"] else 0,
            'price_date': row["price_date"]
        }

    # Process holdings from new JSON format (grouped by ticker)
    data = []
    for ticker, ticker_data in holdings_by_ticker.items():
        # Only include VIP funds
        if ticker not in ticker_info:
            continue

        info = ticker_info[ticker]

        # Process each holding for this ticker
        for holding in ticker_data.get('holdings', []):
            units = holding.get('units', 0)
            value = units * info['price']

            data.append({
                "fund_name": info['mapped_name'],  # Use mapped name from database
                "tax_wrapper": holding.get('tax_wrapper'),
                "platform": holding.get('platform'),
                "ticker": ticker,
                "units": units,
                "price": info['price'],
                "value": value,
                "price_date": info['price_date']
            })

    db.close()
    return pd.DataFrame(data)


def main():
    """Main Streamlit app."""
    st.set_page_config(page_title="Portfolio Viewer", layout="wide")

    st.title("📈 Portfolio Fund Viewer")
    st.markdown("Track your fund transactions and holdings")

    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Current Holdings",
        "📊 Portfolio Overview",
        "🔍 Fund Breakdown",
        "📈 Price History",
        "📋 Mapping Status"
    ])

    # ==================== TAB 1: CURRENT HOLDINGS ====================
    with tab1:
        st.header("💼 Current Holdings (VIP Funds)")
        st.markdown("Your priority fund holdings with current values")

        # Get VIP holdings
        holdings_df = get_current_holdings_vip()

        if holdings_df.empty:
            st.warning("No VIP holdings found. Mark funds as VIP in the fund_ticker_mapping table.")
            return

        # Calculate total portfolio value
        total_value = holdings_df['value'].sum()

        # Display total value at top
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            st.metric("💰 Total Portfolio Value", f"£{total_value:,.2f}")
        with col2:
            vip_count = holdings_df['ticker'].nunique()
            st.metric("📊 VIP Funds", vip_count)
        with col3:
            latest_price_date = holdings_df['price_date'].max() if 'price_date' in holdings_df.columns else "Unknown"
            st.metric("📅 Last Updated", latest_price_date if latest_price_date else "N/A")

        st.divider()

        # ---- Holdings by Fund (Horizontal Stacked Bar Chart) ----
        st.subheader("📈 Holdings by Fund & Tax Wrapper")

        # Color mapping for tax wrappers
        wrapper_colors = {
            'ISA': '#1f77b4',    # Blue
            'SIPP': '#2ca02c',   # Green
            'GIA': '#ff7f0e',    # Orange
            'OTHER': '#d62728'   # Red
        }

        # Create stacked bar chart (funds on Y-axis, wrappers as stacked segments)
        fig = go.Figure()

        # Get unique funds and wrappers
        funds = holdings_df['fund_name'].unique()
        wrappers = ['ISA', 'SIPP', 'GIA', 'OTHER']

        # Add a trace for each tax wrapper
        for wrapper in wrappers:
            wrapper_data = holdings_df[holdings_df['tax_wrapper'] == wrapper]
            if not wrapper_data.empty:
                # Create a list of values for each fund (0 if fund doesn't have this wrapper)
                values = []
                for fund in funds:
                    fund_value = wrapper_data[wrapper_data['fund_name'] == fund]['value'].sum()
                    values.append(fund_value)

                fig.add_trace(go.Bar(
                    name=wrapper,
                    y=funds,
                    x=values,
                    orientation='h',
                    marker=dict(color=wrapper_colors.get(wrapper, '#7f7f7f')),
                    hovertemplate=f'<b>{wrapper}</b><br>%{{y}}<br>Value: £%{{x:,.2f}}<extra></extra>'
                ))

        fig.update_layout(
            title="Holdings by Fund (Stacked by Tax Wrapper)",
            xaxis_title="Value (£)",
            yaxis_title="",
            height=400,
            barmode='stack',
            template="plotly_white",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=200, r=100, t=80, b=50)
        )

        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # ---- Detailed Holdings Table ----
        st.subheader("📋 Detailed Holdings")

        # Tax wrapper filter checkboxes
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            show_isa = st.checkbox("🔵 ISA", value=True, key="show_isa")
        with col_filter2:
            show_sipp = st.checkbox("🟢 SIPP", value=True, key="show_sipp")
        with col_filter3:
            show_gia = st.checkbox("🟠 GIA", value=True, key="show_gia")

        # Filter holdings based on selected tax wrappers
        filtered_df = holdings_df.copy()
        wrapper_filters = []
        if show_isa:
            wrapper_filters.append('ISA')
        if show_sipp:
            wrapper_filters.append('SIPP')
        if show_gia:
            wrapper_filters.append('GIA')

        if wrapper_filters:
            filtered_df = filtered_df[filtered_df['tax_wrapper'].isin(wrapper_filters)]
        else:
            filtered_df = pd.DataFrame()  # Empty if no filters selected

        if not filtered_df.empty:
            # Recalculate total for filtered holdings
            filtered_total = filtered_df['value'].sum()

            # Create display dataframe with raw numeric values for formatting
            display_df = filtered_df.copy()
            display_df['pct_of_portfolio'] = (filtered_df['value'] / total_value * 100)

            # Color code tax wrappers
            def color_tax_wrapper(wrapper):
                colors = {
                    'ISA': '🔵 ISA',
                    'SIPP': '🟢 SIPP',
                    'GIA': '🟠 GIA',
                    'OTHER': '🔴 OTHER'
                }
                return colors.get(wrapper, wrapper)

            display_df['tax_wrapper_colored'] = display_df['tax_wrapper'].apply(color_tax_wrapper)

            # Select and reorder columns for display (Tax Wrapper first)
            display_df = display_df[['tax_wrapper_colored', 'fund_name', 'platform', 'ticker', 'units', 'price', 'value', 'pct_of_portfolio']]
            display_df.columns = ['Tax Wrapper', 'Fund Name', 'Platform', 'Ticker', 'Units', 'Latest Price', 'Current Value', '% of Portfolio']

            # Show filtered total
            st.info(f"Showing {len(display_df)} holdings | Total Value: £{filtered_total:,.2f}")

            # Display table with increased width
            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Tax Wrapper": st.column_config.TextColumn(
                        "Tax Wrapper",
                        width="small"
                    ),
                    "Fund Name": st.column_config.TextColumn(
                        "Fund Name",
                        width="large",
                        help="Fund name from database mapping"
                    ),
                    "Platform": st.column_config.TextColumn(
                        "Platform",
                        width="medium"
                    ),
                    "Ticker": st.column_config.TextColumn(
                        "Ticker",
                        width="medium"
                    ),
                    "Units": st.column_config.NumberColumn(
                        "Units",
                        format="%.2f",
                        width="small"
                    ),
                    "Latest Price": st.column_config.NumberColumn(
                        "Latest Price",
                        format="£%.2f",
                        width="small"
                    ),
                    "Current Value": st.column_config.NumberColumn(
                        "Current Value",
                        format="%.2f",
                        width="medium",
                        help="Current market value of this holding (£)"
                    ),
                    "% of Portfolio": st.column_config.ProgressColumn(
                        "% of Portfolio",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                        width="medium",
                        help="Percentage of total VIP portfolio value"
                    )
                }
            )
        else:
            st.warning("No holdings to display with current filters")

    # ==================== TAB 2: PORTFOLIO OVERVIEW ====================
    with tab2:
        st.header("Portfolio Overview")

        # Get all funds and holdings
        funds_dict = get_all_funds_from_db()
        holdings_df = get_fund_holdings()

        if not funds_dict:
            st.error("No transactions found in the database. Please load transactions first.")
            return

        # ---- All Funds List ----
        st.subheader("📋 All Funds")

        # Get fund counts (excluding excluded funds) with mapped names
        db = TransactionDatabase("portfolio.db")
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT COALESCE(mapped_fund_name, fund_name) as display_name, COUNT(*) as tx_count
            FROM transactions
            WHERE excluded = 0
            GROUP BY COALESCE(mapped_fund_name, fund_name)
            ORDER BY COALESCE(mapped_fund_name, fund_name)
        """)

        funds_list_data = []
        for row in cursor.fetchall():
            funds_list_data.append({
                "Fund Name": row["display_name"],
                "Transactions": row["tx_count"],
            })
        db.close()

        if funds_list_data:
            funds_df = pd.DataFrame(funds_list_data)
            st.dataframe(funds_df, width='stretch', hide_index=True)
        else:
            st.info("No funds found")

    # ==================== TAB 3: FUND BREAKDOWN ====================
    with tab3:
        st.header("Fund Breakdown")

        # Fund selector at the top
        funds_dict = get_all_funds_from_db()

        if not funds_dict:
            st.error("No funds available")
            return

        # Create a selectbox with display names but return original fund names
        fund_keys = list(funds_dict.keys())
        fund_display_names = [funds_dict[k] for k in fund_keys]

        selected_index = st.selectbox(
            "Select a Fund to Analyze",
            options=range(len(fund_keys)),
            format_func=lambda i: fund_display_names[i],
            key="fund_selector",
        )
        selected_fund = fund_keys[selected_index]

        if selected_fund:
            # Get standardized name
            standardized_name = get_standardized_name(selected_fund)

            # Get transactions for this fund
            df = get_fund_transactions(selected_fund)

            if df.empty:
                st.warning(f"No transactions found for {selected_fund}")
            else:
                # Header with fund info
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(f"Fund: {selected_fund}")
                    if standardized_name != selected_fund:
                        st.info(f"📋 Standardized name: **{standardized_name}**")

                # Summary statistics
                st.subheader("Summary")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    total_transactions = len(df)
                    st.metric("Total Transactions", total_transactions)

                with col2:
                    buy_count = len(df[df["Type"] == "BUY"])
                    st.metric("Buy Orders", buy_count)

                with col3:
                    sell_count = len(df[df["Type"] == "SELL"])
                    st.metric("Sell Orders", sell_count)

                with col4:
                    buys_df = df[df["Type"] == "BUY"]
                    sells_df = df[df["Type"] == "SELL"]
                    total_buys = buys_df["Value (£)"].sum() if not buys_df.empty else 0
                    total_sells = sells_df["Value (£)"].sum() if not sells_df.empty else 0
                    net = total_buys - total_sells
                    st.metric("Net (Buys - Sells) (£)", f"£{net:,.2f}")

                # Charts
                st.subheader("Charts")

                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    timeline_fig = create_timeline_chart(df, selected_fund)
                    if timeline_fig:
                        st.plotly_chart(timeline_fig, width='stretch')

                with chart_col2:
                    cumulative_fig = create_cumulative_units_chart(df, selected_fund)
                    if cumulative_fig:
                        st.plotly_chart(cumulative_fig, width='stretch')

                # Transactions table
                st.subheader("All Transactions")

                # Format for display
                df_display = df.copy()
                df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.date
                df_display["Units"] = df_display["Units"].apply(lambda x: f"{x:,.2f}")
                df_display["Price (£)"] = df_display["Price (£)"].apply(lambda x: f"£{x:,.2f}")
                df_display["Value (£)"] = df_display["Value (£)"].apply(lambda x: f"£{x:,.2f}")

                st.dataframe(df_display, width='stretch', hide_index=True)

                # Export option
                st.subheader("Export")
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download Transactions as CSV",
                    data=csv,
                    file_name=f"{selected_fund}_transactions.csv",
                    mime="text/csv",
                )

    # ==================== TAB 4: PRICE HISTORY ====================
    with tab4:
        st.header("Price History")

        # Get all available tickers
        tickers = get_all_price_tickers()
        ticker_info_dict = get_ticker_info_dict()

        if not tickers:
            st.info("No price history data available. Please load the price history data first.")
            return

        # Create a mapping for display
        ticker_to_display = {ticker: f"{ticker} - {ticker_info_dict.get(ticker, 'Unknown')}" for ticker in tickers}

        # Fund/Instrument selector
        selected_ticker = st.selectbox(
            "Select a Fund or Instrument to Analyze",
            options=tickers,
            format_func=lambda t: ticker_to_display[t],
            key="ticker_selector",
        )

        if selected_ticker:
            # Get price history data
            price_df = get_price_history(selected_ticker)
            transactions_df = get_transactions_for_ticker(selected_ticker)
            fund_name = ticker_info_dict.get(selected_ticker, selected_ticker)

            # Determine currency symbol and format
            ticker_currency_map = {
                'BRK-B': '$',
                'EMIM.L': 'p',
                'GB00B2PLJD73': '£',
                'GB00BD6PG787': '£',
                'GB00BF0TZG22': 'p',
                'LU1033663649': '£',
                'MWOT.DE': '€',
                'NVDA': '$',
                'VERG.L': '£',
                'VUAG.L': '£',
                'VWRP.L': '£'
            }
            currency_symbol = ticker_currency_map.get(selected_ticker, '£')

            # Format function based on currency
            if currency_symbol == '$':
                price_format = lambda x: f"${x:.2f}"
            elif currency_symbol == 'p':
                price_format = lambda x: f"{x:.2f}p"
            elif currency_symbol == '€':
                price_format = lambda x: f"€{x:.2f}"
            else:  # £
                price_format = lambda x: f"£{x:.2f}"

            if price_df.empty:
                st.warning(f"No price history found for {selected_ticker}")
            else:
                # Header with ticker info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.subheader(f"Ticker: {selected_ticker}")
                with col2:
                    st.subheader(f"Fund: {fund_name}")
                with col3:
                    latest_price = price_df['Price'].iloc[-1] if not price_df.empty else 0
                    st.metric("Latest Price", price_format(latest_price))

                # Summary statistics - Min Price and Total Change
                st.subheader("Statistics")
                col1, col2 = st.columns(2)

                with col1:
                    min_price = price_df['Price'].min()
                    st.metric("Min Price", price_format(min_price))

                with col2:
                    price_change = price_df['Price'].iloc[-1] - price_df['Price'].iloc[0]
                    pct_change = (price_change / price_df['Price'].iloc[0]) * 100 if price_df['Price'].iloc[0] != 0 else 0
                    st.metric("Total Change", f"{price_format(price_change)} ({pct_change:+.1f}%)")

                # Yearly performance analysis
                st.subheader("Yearly Performance")
                price_df_yearly = price_df.copy()
                price_df_yearly['Year'] = pd.to_datetime(price_df_yearly['Date']).dt.year

                yearly_data = []
                for year in sorted(price_df_yearly['Year'].unique()):
                    year_prices = price_df_yearly[price_df_yearly['Year'] == year]
                    if not year_prices.empty:
                        open_price = year_prices.iloc[0]['Price']
                        close_price = year_prices.iloc[-1]['Price']
                        year_change = close_price - open_price
                        year_pct_change = (year_change / open_price * 100) if open_price != 0 else 0

                        yearly_data.append({
                            'Year': int(year),
                            'Open Price': price_format(open_price),
                            'Close Price': price_format(close_price),
                            'Change %': f"{year_pct_change:+.2f}%"
                        })

                if yearly_data:
                    yearly_df = pd.DataFrame(yearly_data)
                    st.dataframe(yearly_df, width='stretch', hide_index=True)
                else:
                    st.info("No yearly data available")

                # Price chart
                st.subheader("Price Chart")

                # Add toggle for showing transactions
                show_transactions = st.checkbox(
                    "Show buy/sell transactions",
                    value=True,
                    key="show_transactions_toggle"
                )

                # Pass transactions if toggle is on
                transactions_to_show = transactions_df if show_transactions else None
                fig = create_price_chart(price_df, selected_ticker, fund_name, transactions_to_show)
                if fig:
                    st.plotly_chart(fig, width='stretch')

                # Show transaction summary if data exists
                if not transactions_df.empty:
                    buy_count = len(transactions_df[transactions_df['Type'] == 'BUY'])
                    sell_count = len(transactions_df[transactions_df['Type'] == 'SELL'])
                    st.info(
                        f"Found {len(transactions_df)} buy/sell transactions for this ticker "
                        f"({buy_count} buys, {sell_count} sells)"
                    )
                else:
                    st.info("No buy/sell transactions found for this ticker")

                # Price data table - behind a button
                if st.button("Show Price History Data", key="show_price_history_btn"):
                    st.subheader("Price History Data")
                    df_display = price_df.copy()
                    df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.date
                    df_display["Price"] = df_display["Price"].apply(price_format)
                    df_display = df_display[["Date", "Price"]].rename(columns={"Date": "Date", "Price": "Close Price"})

                    st.dataframe(df_display, width='stretch', hide_index=True)

    # ==================== TAB 5: MAPPING STATUS ====================
    with tab5:
        st.header("Mapping Status")
        st.markdown("Overview of fund-to-ticker mappings and price history availability")

        # Get mapping status data
        mapping_df = get_fund_mapping_status()

        if mapping_df.empty:
            st.warning("No funds found in transactions database")
        else:
            # Create display dataframe with checkmarks and crosses
            display_df = mapping_df.copy()
            display_df.rename(columns={
                "fund_name": "Fund Name",
                "mapped_fund_name": "Mapped Name",
                "transaction_count": "Transactions",
                "ticker": "Ticker",
                "has_price_history": "Price History",
                "vip": "VIP"
            }, inplace=True)

            # Format the Price History column with emoji checkmarks/crosses
            display_df["Price History"] = display_df["Price History"].apply(
                lambda x: "✅" if x else "❌"
            )

            # Format the VIP column with star emoji
            display_df["VIP"] = display_df["VIP"].apply(
                lambda x: "⭐" if x else ""
            )

            # Display summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Funds", len(mapping_df))
            with col2:
                mapped_count = (mapping_df["ticker"] != "—").sum()
                st.metric("Mapped to Ticker", mapped_count)
            with col3:
                with_history = mapping_df["has_price_history"].sum()
                st.metric("With Price History", with_history)

            st.divider()

            # Display full table
            st.subheader("Fund Mapping Details")
            st.dataframe(
                display_df,
                width='stretch',
                hide_index=True,
                column_config={
                    "VIP": st.column_config.TextColumn("VIP", width="small"),
                    "Fund Name": st.column_config.TextColumn("Fund Name", width="large"),
                    "Mapped Name": st.column_config.TextColumn("Mapped Name", width="large"),
                    "Transactions": st.column_config.NumberColumn("Transactions", width="small"),
                    "Ticker": st.column_config.TextColumn("Ticker", width="medium"),
                    "Price History": st.column_config.TextColumn("Price History", width="small"),
                }
            )

            # Show unmapped funds if any
            unmapped = mapping_df[mapping_df["ticker"] == "—"]
            if not unmapped.empty:
                st.divider()
                st.subheader(f"Funds Without Mappings ({len(unmapped)})")
                st.warning(f"{len(unmapped)} funds don't have ticker mappings yet")

                unmapped_display = unmapped[["fund_name", "transaction_count"]].copy()
                unmapped_display.rename(columns={
                    "fund_name": "Fund Name",
                    "transaction_count": "Transaction Count"
                }, inplace=True)

                st.dataframe(
                    unmapped_display,
                    width='stretch',
                    hide_index=True
                )


if __name__ == "__main__":
    main()
