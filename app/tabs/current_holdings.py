"""Current Holdings tab for portfolio viewer."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.data import get_current_holdings_vip, get_recent_transactions


# Color mapping for tax wrappers
WRAPPER_COLORS = {
    'ISA': '#1f77b4',    # Blue
    'SIPP': '#2ca02c',   # Green
    'GIA': '#ff7f0e',    # Orange
    'OTHER': '#d62728'   # Red
}


def color_tax_wrapper(wrapper: str) -> str:
    """Add emoji to tax wrapper name."""
    colors = {
        'ISA': '🔵 ISA',
        'SIPP': '🟢 SIPP',
        'GIA': '🟠 GIA',
        'OTHER': '🔴 OTHER'
    }
    return colors.get(wrapper, wrapper)


def color_transaction_type(tx_type: str) -> str:
    """Add emoji to transaction type."""
    if tx_type == 'BUY':
        return '🟢 BUY'
    elif tx_type == 'SELL':
        return '🔴 SELL'
    return tx_type


def render_current_holdings_tab():
    """Render the Current Holdings tab."""
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
        # Get latest price date, filtering out None values
        if 'price_date' in holdings_df.columns:
            valid_dates = holdings_df['price_date'].dropna()
            latest_price_date = valid_dates.max() if not valid_dates.empty else "N/A"
        else:
            latest_price_date = "N/A"
        st.metric("📅 Last Updated", latest_price_date)

    st.divider()

    # ---- Tax wrapper filter checkboxes (horizontal) ----
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        show_isa = st.checkbox("🔵 ISA", value=True, key="show_isa")
    with col_filter2:
        show_sipp = st.checkbox("🟢 SIPP", value=True, key="show_sipp")
    with col_filter3:
        show_gia = st.checkbox("🟠 GIA", value=True, key="show_gia")

    # Determine which tax wrappers to show
    wrapper_filters = []
    if show_isa:
        wrapper_filters.append('ISA')
    if show_sipp:
        wrapper_filters.append('SIPP')
    if show_gia:
        wrapper_filters.append('GIA')

    # Filter holdings based on selected tax wrappers
    if wrapper_filters:
        filtered_holdings_df = holdings_df[holdings_df['tax_wrapper'].isin(wrapper_filters)]
    else:
        filtered_holdings_df = pd.DataFrame()  # Empty if no filters selected

    if filtered_holdings_df.empty:
        st.warning("No holdings to display. Select at least one tax wrapper.")
        return

    # ---- Holdings by Fund (Horizontal Stacked Bar Chart) ----
    st.subheader("📈 Holdings by Fund & Tax Wrapper")

    # Create stacked bar chart using filtered data
    fig = go.Figure()

    # Get unique funds from FILTERED data, sorted by total value (ascending for chart display)
    fund_totals = filtered_holdings_df.groupby('fund_name')['value'].sum().sort_values(ascending=True)
    funds = fund_totals.index.tolist()

    # Add a trace for each selected tax wrapper
    for wrapper in wrapper_filters:
        wrapper_data = filtered_holdings_df[filtered_holdings_df['tax_wrapper'] == wrapper]
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
                marker=dict(color=WRAPPER_COLORS.get(wrapper, '#7f7f7f')),
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

    # ---- Detailed Holdings Table ----
    st.subheader("📋 Detailed Holdings")

    # Get unique platforms for filtering
    all_platforms = sorted(filtered_holdings_df['platform'].unique())

    # Platform filter checkboxes (horizontal multi-select)
    st.write("**Filter by Platform:**")
    platform_cols = st.columns(len(all_platforms) if len(all_platforms) <= 6 else 6)
    selected_platforms = []
    for idx, platform in enumerate(all_platforms):
        col_idx = idx % 6
        with platform_cols[col_idx]:
            if st.checkbox(platform, value=True, key=f"platform_{platform}"):
                selected_platforms.append(platform)

    # Apply platform filter
    if selected_platforms:
        table_filtered_df = filtered_holdings_df[filtered_holdings_df['platform'].isin(selected_platforms)]
    else:
        table_filtered_df = pd.DataFrame()

    if table_filtered_df.empty:
        st.warning("No holdings to display with current filters.")
    else:
        # Sort by value (descending) for display
        table_filtered_df = table_filtered_df.sort_values(by='value', ascending=False)

        # Recalculate total for table filtered holdings
        table_filtered_total = table_filtered_df['value'].sum()

        # Create display dataframe with calculated percentages
        display_df = table_filtered_df.copy()

        # Calculate % of Total Holdings (for each fund across all wrappers/platforms)
        fund_totals = holdings_df.groupby('fund_name')['value'].sum()
        display_df['pct_of_fund'] = display_df.apply(
            lambda row: (row['value'] / fund_totals.get(row['fund_name'], row['value'])) * 100,
            axis=1
        )

        # Calculate % of Wrapper (within the same tax wrapper)
        wrapper_totals = holdings_df.groupby('tax_wrapper')['value'].sum()
        display_df['pct_of_wrapper'] = display_df.apply(
            lambda row: (row['value'] / wrapper_totals.get(row['tax_wrapper'], row['value'])) * 100,
            axis=1
        )

        # Color code tax wrappers
        display_df['tax_wrapper_colored'] = display_df['tax_wrapper'].apply(color_tax_wrapper)

        # Select and reorder columns for Option B display
        display_df = display_df[['tax_wrapper_colored', 'fund_name', 'platform', 'units', 'price', 'value', 'pct_of_fund', 'pct_of_wrapper']]
        display_df.columns = ['Tax Wrapper', 'Fund Name', 'Platform', 'Units', 'Latest Price (£)', 'Current Value (£)', '% of Fund', '% of Wrapper']

        # Show filtered total
        st.info(f"Showing {len(display_df)} holdings | Total Value: £{table_filtered_total:,.2f}")

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
                    width="small"
                ),
                "Units": st.column_config.NumberColumn(
                    "Units",
                    format="%.2f",
                    width="small"
                ),
                "Latest Price (£)": st.column_config.NumberColumn(
                    "Latest Price (£)",
                    format="£%.2f",
                    width="small",
                    help="Current price in GBP (USD converted)"
                ),
                "Current Value (£)": st.column_config.NumberColumn(
                    "Current Value (£)",
                    format="£%.0f",
                    width="medium",
                    help="Current market value in GBP"
                ),
                "% of Fund": st.column_config.ProgressColumn(
                    "% of Fund",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                    width="small",
                    help="Percentage of total holdings for this fund across all wrappers"
                ),
                "% of Wrapper": st.column_config.ProgressColumn(
                    "% of Wrapper",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                    width="small",
                    help="Percentage of total holdings within this tax wrapper"
                )
            }
        )

    # ---- Last 10 Transactions ----
    st.divider()
    st.subheader("📝 Last 10 Transactions")

    recent_tx_df = get_recent_transactions(limit=10)

    if not recent_tx_df.empty:
        display_tx_df = recent_tx_df.copy()
        display_tx_df['Type'] = display_tx_df['Type'].apply(color_transaction_type)
        display_tx_df['Tax Wrapper'] = display_tx_df['Tax Wrapper'].apply(color_tax_wrapper)

        st.dataframe(
            display_tx_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Date": st.column_config.DateColumn(
                    "Date",
                    format="YYYY-MM-DD",
                    width="small"
                ),
                "Fund Name": st.column_config.TextColumn(
                    "Fund Name",
                    width="large"
                ),
                "Type": st.column_config.TextColumn(
                    "Type",
                    width="small"
                ),
                "Units": st.column_config.NumberColumn(
                    "Units",
                    format="%.2f",
                    width="small"
                ),
                "Value (£)": st.column_config.NumberColumn(
                    "Value (£)",
                    format="£%.2f",
                    width="medium"
                ),
                "Platform": st.column_config.TextColumn(
                    "Platform",
                    width="small"
                ),
                "Tax Wrapper": st.column_config.TextColumn(
                    "Tax Wrapper",
                    width="small"
                )
            }
        )
    else:
        st.info("No recent transactions found")