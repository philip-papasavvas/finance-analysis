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
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import TransactionDatabase

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
    """Get the standardized name for a fund."""
    db = TransactionDatabase("portfolio.db")
    standardized = db.get_standardized_name(original_name)
    db.close()
    return standardized


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

    fig = go.Figure()

    # Price line
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Price"],
        fill="tozeroy",
        name="Price",
        line=dict(color="green", width=2),
        hovertemplate="<b>Price</b><br>Date: %{x|%Y-%m-%d}<br>Price: £%{y:.2f}<extra></extra>",
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
    - transaction_count: Number of transactions
    - ticker: Mapped ticker (if available)
    - has_price_history: Boolean indicating if price history exists
    """
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()

    # Get all funds with transaction counts
    cursor.execute("""
        SELECT fund_name, COUNT(*) as transaction_count
        FROM transactions
        WHERE excluded = 0
        GROUP BY fund_name
        ORDER BY transaction_count DESC
    """)

    data = []
    for row in cursor.fetchall():
        fund_name = row["fund_name"]
        transaction_count = row["transaction_count"]

        # Get mapping for this fund
        mapping = db.get_ticker_for_fund(fund_name)
        ticker = mapping if mapping else None

        # Check if we have price history for this ticker
        has_price_history = False
        if ticker:
            cursor.execute("""
                SELECT COUNT(*) as count FROM price_history WHERE ticker = ?
            """, (ticker,))
            result = cursor.fetchone()
            has_price_history = result["count"] > 0 if result else False

        data.append({
            "fund_name": fund_name,
            "transaction_count": transaction_count,
            "ticker": ticker if ticker else "—",
            "has_price_history": has_price_history
        })

    db.close()
    return pd.DataFrame(data)


def main():
    """Main Streamlit app."""
    st.set_page_config(page_title="Portfolio Viewer", layout="wide")

    st.title("📈 Portfolio Fund Viewer")
    st.markdown("Track your fund transactions and holdings")

    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Portfolio Overview", "🔍 Fund Breakdown", "📈 Price History", "📋 Mapping Status"])

    # ==================== TAB 1: PORTFOLIO OVERVIEW ====================
    with tab1:
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

    # ==================== TAB 2: FUND BREAKDOWN ====================
    with tab2:
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
                    total_invested = buys_df["Value (£)"].sum() if not buys_df.empty else 0
                    st.metric("Total Invested (£)", f"£{total_invested:,.2f}")

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

    # ==================== TAB 3: PRICE HISTORY ====================
    with tab3:
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
                    st.metric("Latest Price", f"£{latest_price:.2f}")

                # Summary statistics
                st.subheader("Statistics")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    min_price = price_df['Price'].min()
                    st.metric("Min Price", f"£{min_price:.2f}")

                with col2:
                    max_price = price_df['Price'].max()
                    st.metric("Max Price", f"£{max_price:.2f}")

                with col3:
                    avg_price = price_df['Price'].mean()
                    st.metric("Average Price", f"£{avg_price:.2f}")

                with col4:
                    price_change = price_df['Price'].iloc[-1] - price_df['Price'].iloc[0]
                    pct_change = (price_change / price_df['Price'].iloc[0]) * 100 if price_df['Price'].iloc[0] != 0 else 0
                    st.metric("Total Change", f"£{price_change:.2f} ({pct_change:+.1f}%)")

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

                # Price data table
                st.subheader("Price History Data")
                df_display = price_df.copy()
                df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.date
                df_display["Price"] = df_display["Price"].apply(lambda x: f"£{x:.2f}")
                df_display = df_display[["Date", "Price"]].rename(columns={"Date": "Date", "Price": "Close Price"})

                st.dataframe(df_display, width='stretch', hide_index=True)

    # ==================== TAB 4: MAPPING STATUS ====================
    with tab4:
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
                "transaction_count": "Transactions",
                "ticker": "Ticker",
                "has_price_history": "Price History"
            }, inplace=True)

            # Format the Price History column with emoji checkmarks/crosses
            display_df["Price History"] = display_df["Price History"].apply(
                lambda x: "✅" if x else "❌"
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
                    "Fund Name": st.column_config.TextColumn("Fund Name", width="large"),
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
