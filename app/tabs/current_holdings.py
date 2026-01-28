"""Current Holdings tab for portfolio viewer."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.data import (
    get_current_holdings_vip,
    get_recent_transactions,
    get_aggregated_holdings,
    get_price_history,
)


# Color mapping for tax wrappers
WRAPPER_COLORS = {
    "ISA": "#1f77b4",  # Blue
    "SIPP": "#2ca02c",  # Green
    "GIA": "#ff7f0e",  # Orange
    "OTHER": "#d62728",  # Red
}

# Emoji for tax wrappers
WRAPPER_EMOJI = {
    "ISA": "🔵",
    "SIPP": "🟢",
    "GIA": "🟠",
}


def color_tax_wrapper(wrapper: str) -> str:
    """Add emoji to tax wrapper name."""
    colors = {"ISA": "🔵 ISA", "SIPP": "🟢 SIPP", "GIA": "🟠 GIA", "OTHER": "🔴 OTHER"}
    return colors.get(wrapper, wrapper)


def color_transaction_type(tx_type: str) -> str:
    """Add emoji to transaction type."""
    if tx_type == "BUY":
        return "🟢 BUY"
    elif tx_type == "SELL":
        return "🔴 SELL"
    return tx_type


def render_at_a_glance_section():
    """Render the Portfolio At a Glance section with aggregated holdings."""
    st.subheader("📊 Portfolio At a Glance")
    st.markdown("*Aggregated positions sorted by value • Click to expand breakdown*")

    aggregated = get_aggregated_holdings()

    if not aggregated:
        st.warning("No holdings data available.")
        return

    # Calculate totals
    total_value = sum(h["total_value"] for h in aggregated)
    total_cost = sum(h["cost_basis"] for h in aggregated)
    total_gain = total_value - total_cost
    total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0

    # Summary metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Total Value", f"£{total_value:,.0f}")
    with col2:
        st.metric("💵 Total Cost", f"£{total_cost:,.0f}")
    with col3:
        st.metric("📈 Total Gain/Loss", f"£{total_gain:,.0f}", delta=f"{total_gain_pct:+.1f}%")
    with col4:
        st.metric("🏦 Positions", len(aggregated))

    st.divider()

    # Render each holding as an expandable card
    for holding in aggregated:
        ticker = holding["ticker"]
        fund_name = holding["fund_name"]
        total_units = holding["total_units"]
        price = holding["price"]
        total_value = holding["total_value"]
        cost_basis = holding["cost_basis"]
        gain_loss = holding["gain_loss"]
        gain_loss_pct = holding["gain_loss_pct"]
        holdings_breakdown = holding["holdings"]

        # Determine gain/loss emoji
        gain_emoji = "📈" if gain_loss >= 0 else "📉"

        # Create expander label with key info
        pct_of_portfolio = total_value / sum(h["total_value"] for h in aggregated) * 100
        label = f"**{fund_name}** — £{total_value:,.0f} ({pct_of_portfolio:.1f}%)"

        with st.expander(label, expanded=False):
            # Summary row
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Ticker", ticker)
            with col2:
                st.metric("Total Units", f"{total_units:,.2f}")
            with col3:
                st.metric("Price", f"£{price:,.2f}")
            with col4:
                st.metric("Cost Basis", f"£{cost_basis:,.0f}")
            with col5:
                st.metric(
                    f"{gain_emoji} Gain/Loss",
                    f"£{gain_loss:,.0f}",
                    delta=f"{gain_loss_pct:+.1f}%" if cost_basis > 0 else "N/A",
                )

            # Breakdown table
            if holdings_breakdown:
                st.markdown("**Breakdown by Tax Wrapper & Platform:**")
                breakdown_data = []
                for h in holdings_breakdown:
                    wrapper_emoji = WRAPPER_EMOJI.get(h["tax_wrapper"], "")
                    h_cost = h.get("cost", 0)
                    h_gain = h.get("gain_loss", 0)
                    h_gain_pct = h.get("gain_loss_pct", 0)
                    # Format gain/loss with sign before £
                    gain_sign = "+" if h_gain >= 0 else "-"
                    pct_sign = "+" if h_gain_pct >= 0 else "-"
                    breakdown_data.append(
                        {
                            "Tax Wrapper": f"{wrapper_emoji} {h['tax_wrapper']}",
                            "Platform": h["platform"],
                            "Units": f"{h['units']:,.2f}",
                            "Cost": f"£{h_cost:,.0f}",
                            "Value": f"£{h['value']:,.0f}",
                            "Gain/Loss": f"{gain_sign}£{abs(h_gain):,.0f} ({pct_sign}{abs(h_gain_pct):.1f}%)",
                            "% of Position": f"{(h['value'] / total_value * 100):.1f}%",
                        }
                    )

                breakdown_df = pd.DataFrame(breakdown_data)
                st.dataframe(
                    breakdown_df,
                    hide_index=True,
                    use_container_width=True,
                )

            # Price history chart
            st.markdown("**Price History:**")
            price_df = get_price_history(ticker)
            if not price_df.empty:
                # Create a compact price chart
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=price_df["Date"],
                        y=price_df["Price"],
                        fill="tozeroy",
                        name="Price",
                        line=dict(color="#22c55e" if gain_loss >= 0 else "#ef4444", width=2),
                        hovertemplate="<b>%{x|%Y-%m-%d}</b><br>Price: £%{y:.2f}<extra></extra>",
                    )
                )
                fig.update_layout(
                    height=250,
                    margin=dict(l=0, r=0, t=10, b=0),
                    xaxis=dict(showgrid=False, showticklabels=True),
                    yaxis=dict(showgrid=True, gridcolor="#e5e5e5", tickprefix="£"),
                    template="plotly_white",
                    showlegend=False,
                    hovermode="x unified",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No price history available for this ticker.")


def render_current_holdings_tab():
    """Render the Current Holdings tab."""
    st.header("💼 Current Holdings")

    # View selector
    view_mode = st.radio(
        "Select View",
        ["📊 At a Glance", "📋 Detailed View"],
        horizontal=True,
        key="holdings_view_mode",
    )

    st.divider()

    if view_mode == "📊 At a Glance":
        render_at_a_glance_section()
        return

    # ---- Detailed View (existing code) ----
    st.subheader("📋 Detailed Holdings by Wrapper & Platform")

    # Get VIP holdings
    holdings_df = get_current_holdings_vip()

    if holdings_df.empty:
        st.warning("No VIP holdings found. Mark funds as VIP in the fund_ticker_mapping table.")
        return

    # Calculate total portfolio value
    total_value = holdings_df["value"].sum()

    # Display total value at top
    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        st.metric("💰 Total Portfolio Value", f"£{total_value:,.2f}")
    with col2:
        vip_count = holdings_df["ticker"].nunique()
        st.metric("📊 VIP Funds", vip_count)
    with col3:
        # Get latest price date, filtering out None values
        if "price_date" in holdings_df.columns:
            valid_dates = holdings_df["price_date"].dropna()
            latest_price_date = valid_dates.max() if not valid_dates.empty else "N/A"
        else:
            latest_price_date = "N/A"
        st.metric("📅 Last Updated", latest_price_date)

    st.divider()

    # ---- Tax wrapper filter checkboxes (horizontal) ----
    st.write("**Filter by Tax Wrapper:**")
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
        wrapper_filters.append("ISA")
    if show_sipp:
        wrapper_filters.append("SIPP")
    if show_gia:
        wrapper_filters.append("GIA")

    # Filter holdings based on selected tax wrappers
    if wrapper_filters:
        filtered_holdings_df = holdings_df[holdings_df["tax_wrapper"].isin(wrapper_filters)]
    else:
        filtered_holdings_df = pd.DataFrame()  # Empty if no filters selected

    if filtered_holdings_df.empty:
        st.warning("No holdings to display. Select at least one tax wrapper.")
        return

    # ---- Platform filter checkboxes (horizontal) ----
    st.write("**Filter by Platform:**")
    all_platforms = sorted(filtered_holdings_df["platform"].unique())
    platform_cols = st.columns(len(all_platforms) if len(all_platforms) <= 6 else 6)
    selected_platforms = []
    for idx, platform in enumerate(all_platforms):
        col_idx = idx % 6
        with platform_cols[col_idx]:
            if st.checkbox(platform, value=True, key=f"platform_{platform}"):
                selected_platforms.append(platform)

    # Apply platform filter
    if selected_platforms:
        filtered_holdings_df = filtered_holdings_df[
            filtered_holdings_df["platform"].isin(selected_platforms)
        ]
    else:
        filtered_holdings_df = pd.DataFrame()

    if filtered_holdings_df.empty:
        st.warning("No holdings to display with current filters.")
        return

    # ---- Holdings by Fund (Horizontal Stacked Bar Chart) ----
    st.subheader("📈 Holdings by Fund & Tax Wrapper")

    # Create stacked bar chart using filtered data
    fig = go.Figure()

    # Get unique funds from FILTERED data, sorted by total value (ascending for chart display)
    fund_totals = (
        filtered_holdings_df.groupby("fund_name")["value"].sum().sort_values(ascending=True)
    )
    funds = fund_totals.index.tolist()

    # Add a trace for each selected tax wrapper
    for wrapper in wrapper_filters:
        wrapper_data = filtered_holdings_df[filtered_holdings_df["tax_wrapper"] == wrapper]
        if not wrapper_data.empty:
            # Create a list of values for each fund (0 if fund doesn't have this wrapper)
            values = []
            for fund in funds:
                fund_value = wrapper_data[wrapper_data["fund_name"] == fund]["value"].sum()
                values.append(fund_value)

            fig.add_trace(
                go.Bar(
                    name=wrapper,
                    y=funds,
                    x=values,
                    orientation="h",
                    marker=dict(color=WRAPPER_COLORS.get(wrapper, "#7f7f7f")),
                    hovertemplate=f"<b>{wrapper}</b><br>%{{y}}<br>Value: £%{{x:,.2f}}<extra></extra>",
                )
            )

    fig.update_layout(
        title="Holdings by Fund (Stacked by Tax Wrapper)",
        xaxis_title="Value (£)",
        yaxis_title="",
        height=400,
        barmode="stack",
        template="plotly_white",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=200, r=100, t=80, b=50),
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---- Detailed Holdings Table ----
    st.subheader("📋 Detailed Holdings")

    # Use filtered_holdings_df which already has platform filter applied
    table_filtered_df = filtered_holdings_df.copy()

    if table_filtered_df.empty:
        st.warning("No holdings to display with current filters.")
    else:
        # Sort by value (descending) for display
        table_filtered_df = table_filtered_df.sort_values(by="value", ascending=False)

        # Recalculate total for table filtered holdings
        table_filtered_total = table_filtered_df["value"].sum()

        # Create display dataframe with calculated percentages
        display_df = table_filtered_df.copy()

        # Calculate % of Total Holdings (for each fund across all wrappers/platforms)
        fund_totals = holdings_df.groupby("fund_name")["value"].sum()
        display_df["pct_of_fund"] = display_df.apply(
            lambda row: (row["value"] / fund_totals.get(row["fund_name"], row["value"])) * 100,
            axis=1,
        )

        # Calculate % of Wrapper (within the same tax wrapper)
        wrapper_totals = holdings_df.groupby("tax_wrapper")["value"].sum()
        display_df["pct_of_wrapper"] = display_df.apply(
            lambda row: (row["value"] / wrapper_totals.get(row["tax_wrapper"], row["value"])) * 100,
            axis=1,
        )

        # Color code tax wrappers
        display_df["tax_wrapper_colored"] = display_df["tax_wrapper"].apply(color_tax_wrapper)

        # Select and reorder columns for Option B display
        display_df = display_df[
            [
                "tax_wrapper_colored",
                "fund_name",
                "platform",
                "units",
                "price",
                "value",
                "pct_of_fund",
                "pct_of_wrapper",
            ]
        ]
        display_df.columns = [
            "Tax Wrapper",
            "Fund Name",
            "Platform",
            "Units",
            "Latest Price (£)",
            "Current Value (£)",
            "% of Fund",
            "% of Wrapper",
        ]

        # Format numeric columns with thousand separators
        display_df["Units"] = display_df["Units"].apply(lambda x: f"{x:,.2f}")
        display_df["Latest Price (£)"] = display_df["Latest Price (£)"].apply(
            lambda x: f"£{x:,.2f}"
        )
        display_df["Current Value (£)"] = display_df["Current Value (£)"].apply(
            lambda x: f"£{x:,.0f}"
        )

        # Show filtered total
        st.info(f"Showing {len(display_df)} holdings | Total Value: £{table_filtered_total:,.2f}")

        # Display table with increased width
        st.dataframe(
            display_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Tax Wrapper": st.column_config.TextColumn("Tax Wrapper", width="small"),
                "Fund Name": st.column_config.TextColumn(
                    "Fund Name", width="large", help="Fund name from database mapping"
                ),
                "Platform": st.column_config.TextColumn("Platform", width="small"),
                "Units": st.column_config.TextColumn("Units", width="small"),
                "Latest Price (£)": st.column_config.TextColumn(
                    "Latest Price (£)",
                    width="small",
                    help="Current price in GBP (USD/EUR converted)",
                ),
                "Current Value (£)": st.column_config.TextColumn(
                    "Current Value (£)", width="medium", help="Current market value in GBP"
                ),
                "% of Fund": st.column_config.ProgressColumn(
                    "% of Fund",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                    width="small",
                    help="Percentage of total holdings for this fund across all wrappers",
                ),
                "% of Wrapper": st.column_config.ProgressColumn(
                    "% of Wrapper",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                    width="small",
                    help="Percentage of total holdings within this tax wrapper",
                ),
            },
        )

    # ---- Last 10 Transactions ----
    st.divider()
    st.subheader("📝 Last 10 Transactions")

    recent_tx_df = get_recent_transactions(limit=10)

    if not recent_tx_df.empty:
        display_tx_df = recent_tx_df.copy()
        display_tx_df["Type"] = display_tx_df["Type"].apply(color_transaction_type)
        display_tx_df["Tax Wrapper"] = display_tx_df["Tax Wrapper"].apply(color_tax_wrapper)

        # Format numeric columns with thousand separators
        display_tx_df["Units"] = display_tx_df["Units"].apply(
            lambda x: f"{float(x):,.2f}" if pd.notna(x) else ""
        )
        display_tx_df["Value (£)"] = display_tx_df["Value (£)"].apply(
            lambda x: f"£{float(x):,.2f}" if pd.notna(x) else ""
        )

        st.dataframe(
            display_tx_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD", width="small"),
                "Fund Name": st.column_config.TextColumn("Fund Name", width="large"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Units": st.column_config.TextColumn("Units", width="small"),
                "Value (£)": st.column_config.TextColumn("Value (£)", width="medium"),
                "Platform": st.column_config.TextColumn("Platform", width="small"),
                "Tax Wrapper": st.column_config.TextColumn("Tax Wrapper", width="small"),
            },
        )
    else:
        st.info("No recent transactions found")
