"""
Streamlit app for analyzing credit card spending from CSV exports.

Supports Yonder transaction exports with categorization, trend analysis,
and merchant breakdown. Provides filters for date ranges and categories.
"""
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Setup logging (following portfolio_viewer.py pattern)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = Path(__file__).parent.parent / 'data' / 'credit_card'
CSV_FILE = DATA_DIR / 'transactions.csv'


@st.cache_data
def load_data():
    """
    Load credit card transactions from CSV file with date parsing.

    Returns:
        pd.DataFrame: Transaction data with parsed dates and derived fields,
                     or empty DataFrame if file not found.
    """
    try:
        # Load CSV
        df = pd.read_csv(CSV_FILE)

        # Parse Dates (Handling the YYYY-MMM-DD format)
        df['Date'] = pd.to_datetime(df['Date'], format='%Y-%b-%d')

        # Extract Month-Year for filtering/grouping
        df['Month'] = df['Date'].dt.strftime('%Y-%m')
        df['Week_Start'] = df['Date'].dt.to_period('W').apply(lambda r: r.start_time)

        logger.info(f"Loaded {len(df)} transactions from {CSV_FILE}")
        return df
    except FileNotFoundError:
        logger.error(f"File not found: {CSV_FILE}")
        st.error(f"❌ Transaction file not found: {CSV_FILE}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame()


def highlight_refunds(val):
    """
    Apply red color styling to negative values (refunds).

    Args:
        val: Numeric value to style

    Returns:
        str: CSS color styling string
    """
    color = 'red' if val < 0 else 'black'
    return f'color: {color}'


def main():
    """Main Streamlit app for credit card spending analysis."""
    st.set_page_config(page_title="Yonder Spend Analyzer", layout="wide")

    # Load data
    df = load_data()

    if df.empty:
        st.warning("No data available.")
        return

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filter Transactions")

    # 1. Choose Amount Type
    amount_col = st.sidebar.radio(
        "Which amounts to analyze?",
        ('Adjusted_Amount', 'Original_Amount'),
        index=0,
        help="Adjusted removes split bills (Three Daggers) and reimbursable flights."
    )

    # 2. Category Filter
    all_categories = sorted(df['Category'].unique())
    selected_categories = st.sidebar.multiselect(
        "Category",
        all_categories,
        default=all_categories
    )

    # 3. Month Filter
    all_months = sorted(df['Month'].unique())
    selected_months = st.sidebar.multiselect("Month", all_months, default=all_months)

    # Apply Filters
    filtered_df = df[
        (df['Category'].isin(selected_categories)) &
        (df['Month'].isin(selected_months))
    ]

    # --- MAIN DASHBOARD ---
    st.title("💳 Yonder Spending Insights")
    st.markdown(
        f"Analyzing spending from **{filtered_df['Date'].min().date()}** to **{filtered_df['Date'].max().date()}**"
    )

    # --- TOP METRICS ---
    total_spend = filtered_df[amount_col].sum()
    avg_monthly_spend = total_spend / filtered_df['Month'].nunique()

    # Find highest spend category
    cat_group = filtered_df.groupby('Category')[amount_col].sum()
    top_cat = cat_group.idxmax()
    top_cat_val = cat_group.max()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Net Spend", f"£{total_spend:,.2f}")
    col2.metric("Avg Monthly Spend", f"£{avg_monthly_spend:,.2f}")
    col3.metric("Top Category", top_cat, f"£{top_cat_val:,.0f}")
    col4.metric("Transactions", len(filtered_df))

    st.markdown("---")

    # --- ROW 1: SPEND OVER TIME & CATEGORY BREAKDOWN ---
    row1_col1, row1_col2 = st.columns([2, 1])

    with row1_col1:
        st.subheader("Weekly Spending Trend")
        weekly_spend = filtered_df.groupby('Week_Start')[amount_col].sum().reset_index()
        fig_trend = px.line(
            weekly_spend,
            x='Week_Start',
            y=amount_col,
            markers=True,
            title="Net Spend per Week"
        )
        fig_trend.update_layout(xaxis_title="Week Commencing", yaxis_title="Spend (£)")
        st.plotly_chart(fig_trend, use_container_width=True)

    with row1_col2:
        st.subheader("Category Breakdown")
        fig_pie = px.pie(
            filtered_df,
            values=amount_col,
            names='Category',
            hole=0.4,
            title="Share of Wallet"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- ROW 2: DETAILED ANALYSIS ---
    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        st.subheader("Top Merchants (by Net Spend)")
        merchant_spend = filtered_df.groupby('Description')[amount_col].sum().reset_index()
        merchant_spend = merchant_spend.sort_values(by=amount_col, ascending=False).head(10)
        st.dataframe(
            merchant_spend.style.format({amount_col: "£{:.2f}"}),
            use_container_width=True,
            hide_index=True
        )

    with row2_col2:
        st.subheader("Spend Type: One-Off vs Recurring")
        # Ensure 'Type' column exists (it's in the CSV provided)
        if 'Type' in filtered_df.columns:
            type_spend = filtered_df.groupby('Type')[amount_col].sum().reset_index()
            fig_bar = px.bar(
                type_spend,
                x='Type',
                y=amount_col,
                color='Type',
                title="Regular vs. Impulse Spending"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No 'Type' column found in CSV.")

    st.markdown("---")

    # --- DATA TABLE ---
    st.subheader("Detailed Transaction Log")
    st.markdown("Use the column headers to sort.")

    # Format the display dataframe for readability
    display_df = filtered_df[
        ['Date', 'Description', 'Category', 'Original_Amount', 'Adjusted_Amount', 'Type', 'Notes']
    ].copy()
    display_df['Date'] = display_df['Date'].dt.date

    st.dataframe(
        display_df.style.format({
            'Original_Amount': "£{:.2f}",
            'Adjusted_Amount': "£{:.2f}"
        }).map(highlight_refunds, subset=['Adjusted_Amount']),
        use_container_width=True
    )


if __name__ == "__main__":
    main()