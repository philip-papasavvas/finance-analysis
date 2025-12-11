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
    """Get all unique funds from the database."""
    db = TransactionDatabase("portfolio.db")
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT DISTINCT fund_name FROM transactions ORDER BY fund_name
    """)
    funds = [row["fund_name"] for row in cursor.fetchall()]
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
            transaction_type,
            units,
            price_per_unit,
            value,
            currency
        FROM transactions
        WHERE fund_name = ?
        ORDER BY date
    """, (fund_name,))

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
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    # Calculate cumulative units (buys are positive, sells are negative)
    df["Cumulative Units"] = 0
    cumulative = 0

    for idx, row in df.iterrows():
        if row["Type"] == "BUY":
            cumulative += row["Units"]
        else:  # SELL
            cumulative -= row["Units"]
        df.at[idx, "Cumulative Units"] = cumulative

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


def main():
    """Main Streamlit app."""
    st.set_page_config(page_title="Portfolio Viewer", layout="wide")

    st.title("📈 Portfolio Fund Viewer")
    st.markdown("Track your fund transactions with interactive charts and filtering")

    # Sidebar
    st.sidebar.header("Fund Selection")

    # Load all funds
    all_funds = get_all_funds_from_db()

    if not all_funds:
        st.error("No transactions found in the database. Please load transactions first.")
        return

    # Fund selector
    selected_fund = st.sidebar.selectbox(
        "Select a Fund",
        options=all_funds,
        format_func=lambda x: f"{x}",
    )

    if selected_fund:
        # Get standardized name
        standardized_name = get_standardized_name(selected_fund)

        # Get transactions for this fund
        df = get_fund_transactions(selected_fund)

        if df.empty:
            st.warning(f"No transactions found for {selected_fund}")
            return

        # Header with fund info
        col1, col2 = st.columns([3, 1])
        with col1:
            st.header(f"Fund: {selected_fund}")
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
                st.plotly_chart(timeline_fig, use_container_width=True)

        with chart_col2:
            cumulative_fig = create_cumulative_units_chart(df, selected_fund)
            if cumulative_fig:
                st.plotly_chart(cumulative_fig, use_container_width=True)

        # Transactions table
        st.subheader("All Transactions")

        # Format for display
        df_display = df.copy()
        df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.date
        df_display["Units"] = df_display["Units"].apply(lambda x: f"{x:,.2f}")
        df_display["Price (£)"] = df_display["Price (£)"].apply(lambda x: f"£{x:,.2f}")
        df_display["Value (£)"] = df_display["Value (£)"].apply(lambda x: f"£{x:,.2f}")

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Export option
        st.subheader("Export")
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Transactions as CSV",
            data=csv,
            file_name=f"{selected_fund}_transactions.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()