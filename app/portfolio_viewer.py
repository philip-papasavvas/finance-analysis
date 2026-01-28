"""
Streamlit app for viewing portfolio transactions with interactive fund selection.

This is the main entry point for the Portfolio Fund Viewer application.
The app is organized into separate modules:
- app.data: Database queries and data access
- app.charts: Chart creation functions
- app.tabs: Individual tab rendering functions
"""

import logging

import streamlit as st

from app.tabs import (
    render_current_holdings_tab,
    render_transaction_history_tab,
    render_price_history_tab,
    render_mapping_status_tab,
    render_portfolio_performance_tab,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    """Main Streamlit app."""
    st.set_page_config(page_title="Portfolio Viewer", layout="wide")

    st.title("📈 Portfolio Fund Viewer")

    # Create tabs
    holdings_tab, performance_tab, transactions_tab, prices_tab, mapping_tab = st.tabs(
        [
            "🏠 Current Holdings",
            "💹 Portfolio Performance",
            "🔍 Transaction History",
            "📈 Price History",
            "📋 Mapping Status",
        ]
    )

    # Render each tab
    with holdings_tab:
        render_current_holdings_tab()

    with performance_tab:
        render_portfolio_performance_tab()

    with transactions_tab:
        render_transaction_history_tab()

    with prices_tab:
        render_price_history_tab()

    with mapping_tab:
        render_mapping_status_tab()


if __name__ == "__main__":
    main()
