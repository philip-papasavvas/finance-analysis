"""Price History tab for portfolio viewer."""

import pandas as pd
import streamlit as st

from app.data import get_all_price_tickers, get_ticker_info_dict, get_price_history, get_transactions_for_ticker
from app.charts import create_price_chart


# Currency symbol mapping for tickers
TICKER_CURRENCY_MAP = {
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


def get_price_format(currency_symbol: str):
    """Get a price formatting function for the given currency symbol."""
    if currency_symbol == '$':
        return lambda x: f"${x:.2f}"
    elif currency_symbol == 'p':
        return lambda x: f"{x:.2f}p"
    elif currency_symbol == '€':
        return lambda x: f"€{x:.2f}"
    else:  # £
        return lambda x: f"£{x:.2f}"


def render_price_history_tab():
    """Render the Price History tab."""
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
        currency_symbol = TICKER_CURRENCY_MAP.get(selected_ticker, '£')
        price_format = get_price_format(currency_symbol)

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