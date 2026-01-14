"""
Streamlit app for analyzing credit card spending from CSV exports.

Automatically loads and combines transactions from all CSV files in the
data/credit_card directory. Supports multiple card providers (Yonder, Chase,
Monzo, etc.) with automatic format detection and normalization.

Features:
- Multi-card analysis with source filtering
- Category and time-based filtering
- Weekly spending trends with rolling averages
- Top merchants and recurring vs one-off spend analysis
- Detailed transaction table with refund highlighting
"""
import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Setup logging (following portfolio_viewer.py pattern)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Constants
DATA_DIR = Path(__file__).parent.parent / "data" / "credit_card"


@st.cache_data
def load_data():
    """
    Load credit card transactions from all CSV files in the credit_card directory.

    Automatically detects CSV format (single Amount column vs Original_Amount/Adjusted_Amount)
    and normalizes to a consistent format. Derives card source from filename.

    Returns:
        pd.DataFrame: Combined transaction data with parsed dates, derived fields,
                     and 'Source' column indicating card provider.
    """
    dfs = []
    csv_files = list(DATA_DIR.glob("*.csv"))

    if not csv_files:
        st.error(f"❌ No CSV files found in {DATA_DIR}")
        return pd.DataFrame()

    for csv_file in csv_files:
        try:
            # Extract card name from filename (e.g., "yonder_transactions_..." -> "Yonder")
            card_name = csv_file.stem.split("_")[0].capitalize()

            df = pd.read_csv(csv_file)
            df["Source"] = card_name

            # Parse dates
            df["Date"] = pd.to_datetime(df["Date"], format="%Y-%b-%d")

            # Normalize amount columns based on CSV format
            if "Amount" in df.columns:
                # Single Amount column (e.g., Chase, Monzo) - duplicate to match Yonder format
                df["Original_Amount"] = df["Amount"]
                df["Adjusted_Amount"] = df["Amount"]
                df = df.drop(columns=["Amount"])
            elif "Original_Amount" not in df.columns or "Adjusted_Amount" not in df.columns:
                logger.error(f"Skipping {csv_file.name}: Missing required amount columns")
                st.warning(f"⚠️ Skipped {csv_file.name}: Invalid format")
                continue

            logger.info(f"Loaded {len(df)} transactions from {card_name} ({csv_file.name})")
            dfs.append(df)

        except Exception as e:
            logger.error(f"Error loading {csv_file.name}: {e}")
            st.error(f"❌ Error loading {csv_file.name}: {e}")

    if not dfs:
        st.error("❌ No valid transaction data found")
        return pd.DataFrame()

    # Combine all sources
    df = pd.concat(dfs, ignore_index=True)

    # Extract Month-Year for filtering/grouping
    df["Month"] = df["Date"].dt.strftime("%Y-%m")
    df["Week_Start"] = df["Date"].dt.to_period("W").apply(lambda r: r.start_time)

    logger.info(f"Combined total: {len(df)} transactions from {len(dfs)} sources")
    return df


def highlight_refunds(val):
    """
    Apply red color styling to negative values (refunds).

    Args:
        val: Numeric value to style

    Returns:
        str: CSS color styling string
    """
    color = "red" if val < 0 else "white"
    return f"color: {color}"


def main():
    """Main Streamlit app for credit card spending analysis."""
    st.set_page_config(page_title="Credit Card Spend Analyzer", layout="wide")

    # Load data
    df = load_data()

    if df.empty:
        st.warning("No data available.")
        return

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filter Transactions")

    # 1. Card Source Filter
    all_sources = sorted(df["Source"].unique())
    selected_sources = st.sidebar.multiselect("Card", all_sources, default=all_sources)

    # 2. Choose Amount Type
    amount_col = st.sidebar.radio(
        "Which amounts to analyze?",
        ("Adjusted_Amount", "Original_Amount"),
        index=0,
        help="Adjusted removes split bills (Three Daggers) and reimbursable flights.",
    )

    # 3. Category Filter
    all_categories = sorted(df["Category"].unique())
    selected_categories = st.sidebar.multiselect("Category", all_categories, default=all_categories)

    # 4. Month Filter
    all_months = sorted(df["Month"].unique())
    selected_months = st.sidebar.multiselect("Month", all_months, default=all_months)

    # Apply Filters
    filtered_df = df[
        (df["Source"].isin(selected_sources))
        & (df["Category"].isin(selected_categories))
        & (df["Month"].isin(selected_months))
    ]

    # --- MAIN DASHBOARD ---
    st.title("💳 Credit Card Spending Insights")

    # Show which cards are being analyzed
    card_list = ", ".join(sorted(filtered_df["Source"].unique()))
    st.markdown(
        f"Analyzing **{card_list}** from **{filtered_df['Date'].min().date()}** to **{filtered_df['Date'].max().date()}**"
    )

    # --- TOP METRICS ---
    total_spend = filtered_df[amount_col].sum()
    avg_monthly_spend = total_spend / filtered_df["Month"].nunique()

    # Find highest spend category
    cat_group = filtered_df.groupby("Category")[amount_col].sum()
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
        weekly_spend = filtered_df.groupby("Week_Start")[amount_col].sum().reset_index()

        # Calculate average weekly spend
        avg_weekly_spend = weekly_spend[amount_col].mean()

        fig_trend = px.line(
            weekly_spend, x="Week_Start", y=amount_col, markers=True, title="Net Spend per Week"
        )

        # Add dotted horizontal line for overall average
        fig_trend.add_hline(
            y=avg_weekly_spend,
            line_dash="dot",
            line_color="gray",
            annotation_text=f"Overall Avg: £{avg_weekly_spend:,.2f}",
            annotation_position="right",
        )

        fig_trend.update_layout(
            xaxis_title="Week Commencing", yaxis_title="Spend (£)", showlegend=False
        )
        st.plotly_chart(fig_trend, width="stretch")

    with row1_col2:
        st.subheader("Category Breakdown")
        fig_pie = px.pie(
            filtered_df, values=amount_col, names="Category", hole=0.4, title="Share of Wallet"
        )
        st.plotly_chart(fig_pie, width="stretch")

    st.markdown("---")

    # --- MONTHLY BREAKDOWN BY CARD ---
    st.subheader("Monthly Spending by Card Provider")

    # Group by Month and Source
    monthly_by_card = filtered_df.groupby(["Month", "Source"])[amount_col].sum().reset_index()

    # Create grouped bar chart (shows each card as separate bar)
    fig_monthly = px.bar(
        monthly_by_card,
        x="Month",
        y=amount_col,
        color="Source",
        title="Monthly Spend Breakdown by Card",
        barmode="group",
        text_auto=".2f",
    )

    fig_monthly.update_layout(
        xaxis_title="Month",
        yaxis_title="Spend (£)",
        legend_title="Card Provider",
        hovermode="x unified",
    )

    st.plotly_chart(fig_monthly, use_container_width=True)

    st.markdown("---")

    # --- ROW 2: DETAILED ANALYSIS ---
    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        st.subheader("Top Merchants (by Net Spend)")
        merchant_spend = filtered_df.groupby("Description")[amount_col].sum().reset_index()
        merchant_spend = merchant_spend.sort_values(by=amount_col, ascending=False).head(10)
        st.dataframe(
            merchant_spend.style.format({amount_col: "£{:.2f}"}), width="stretch", hide_index=True
        )

    with row2_col2:
        st.subheader("Spend Type: One-Off vs Recurring")
        # Ensure 'Type' column exists (it's in the CSV provided)
        if "Type" in filtered_df.columns:
            type_spend = filtered_df.groupby("Type")[amount_col].sum().reset_index()
            fig_bar = px.bar(
                type_spend,
                x="Type",
                y=amount_col,
                color="Type",
                title="Regular vs. Impulse Spending",
            )
            st.plotly_chart(fig_bar, width="stretch")
        else:
            st.info("No 'Type' column found in CSV.")

    st.markdown("---")

    # --- DATA TABLE ---
    st.subheader("Detailed Transaction Log")
    st.markdown("Use the column headers to sort.")

    # Format the display dataframe for readability
    display_df = filtered_df[
        [
            "Date",
            "Source",
            "Description",
            "Category",
            "Original_Amount",
            "Adjusted_Amount",
            "Type",
            "Notes",
        ]
    ].copy()
    display_df["Date"] = display_df["Date"].dt.date

    st.dataframe(
        display_df.style.format({"Original_Amount": "£{:.2f}", "Adjusted_Amount": "£{:.2f}"}).map(
            highlight_refunds, subset=["Adjusted_Amount"]
        ),
        width="stretch",
    )


if __name__ == "__main__":
    main()
