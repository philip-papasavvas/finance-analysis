"""Funds List tab for portfolio viewer."""

import pandas as pd
import streamlit as st

from portfolio.core.database import TransactionDatabase
from app.data import sql, get_all_funds_from_db, get_fund_holdings


def render_funds_list_tab():
    """Render the Funds List tab."""
    st.header("Funds List")

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
    cursor.execute(sql.GET_FUNDS_WITH_COUNTS)

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