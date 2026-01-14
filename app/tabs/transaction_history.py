"""Transaction History tab for portfolio viewer."""

import pandas as pd
import streamlit as st

from app.data import get_all_funds_from_db, get_fund_transactions, get_standardized_name
from app.charts import create_timeline_chart, create_cumulative_units_chart


def render_transaction_history_tab():
    """Render the Transaction History tab."""
    st.header("Transaction History")

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
                    st.plotly_chart(timeline_fig, width="stretch")

            with chart_col2:
                cumulative_fig = create_cumulative_units_chart(df, selected_fund)
                if cumulative_fig:
                    st.plotly_chart(cumulative_fig, width="stretch")

            # Transactions table
            st.subheader("All Transactions")

            # Format for display
            df_display = df.copy()
            df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.date
            df_display["Units"] = df_display["Units"].apply(lambda x: f"{x:,.2f}")
            df_display["Price (£)"] = df_display["Price (£)"].apply(lambda x: f"£{x:,.2f}")
            df_display["Value (£)"] = df_display["Value (£)"].apply(lambda x: f"£{x:,.2f}")

            st.dataframe(df_display, width="stretch", hide_index=True)

            # Export option
            st.subheader("Export")
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Transactions as CSV",
                data=csv,
                file_name=f"{selected_fund}_transactions.csv",
                mime="text/csv",
            )
