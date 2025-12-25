"""Mapping Status tab for portfolio viewer."""

import streamlit as st

from app.data import get_fund_mapping_status


def render_mapping_status_tab():
    """Render the Mapping Status tab."""
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