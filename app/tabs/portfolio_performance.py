"""Portfolio Performance tab for portfolio viewer - Simply Wall St inspired design."""

import streamlit as st
import numpy as np

from app.data import get_portfolio_value_timeseries, get_current_holdings_vip
from app.charts import (
    create_portfolio_performance_chart,
    TIME_RANGES,
    filter_dataframe_by_time_range,
)


def calculate_annualized_irr(df, time_range: str) -> float:
    """Calculate annualized IRR for the portfolio over the given time range."""
    filtered_df = filter_dataframe_by_time_range(df, time_range)
    if filtered_df.empty or len(filtered_df) < 2:
        return 0.0

    start_value = filtered_df["Value"].iloc[0]
    end_value = filtered_df["Value"].iloc[-1]
    start_date = filtered_df["Date"].iloc[0]
    end_date = filtered_df["Date"].iloc[-1]

    # Calculate years between dates
    days = (end_date - start_date).days
    if days <= 0:
        return 0.0
    years = days / 365.25

    # Calculate annualized return (CAGR)
    if start_value <= 0:
        return 0.0

    total_return = end_value / start_value
    if total_return <= 0:
        return 0.0

    annualized_return = (total_return ** (1 / years) - 1) * 100
    return annualized_return


def render_portfolio_performance_tab():
    """Render the Portfolio Performance tab with Simply Wall St inspired design."""

    # Custom CSS for dark theme styling
    st.markdown(
        """
    <style>
    .performance-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: #1a1a2e;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
        color: #ffffff;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #9ca3af;
    }
    .metric-delta-positive {
        color: #22c55e;
        font-size: 0.9rem;
    }
    .metric-delta-negative {
        color: #ef4444;
        font-size: 0.9rem;
    }
    .time-range-btn {
        background: #2d2d44;
        border: none;
        color: #9ca3af;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        cursor: pointer;
    }
    .time-range-btn-active {
        background: #3b82f6;
        color: white;
    }
    .bottom-metric {
        background: #1a1a2e;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid #3b82f6;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Initialize session state for time range
    if "perf_time_range" not in st.session_state:
        st.session_state.perf_time_range = "1Y"

    # Fetch portfolio data with benchmark
    portfolio_df = get_portfolio_value_timeseries(include_benchmark=True, benchmark_ticker="VWRL.L")

    if portfolio_df.empty:
        st.warning("No portfolio data available. Ensure you have transactions and price history.")
        return

    # Get current holdings for additional metrics
    holdings_df = get_current_holdings_vip()

    # Calculate total portfolio value from current holdings
    total_value = (
        holdings_df["value"].sum() if not holdings_df.empty else portfolio_df["Value"].iloc[-1]
    )

    # Filter data for selected time range
    selected_range = st.session_state.perf_time_range
    filtered_df = filter_dataframe_by_time_range(portfolio_df, selected_range)

    if filtered_df.empty:
        st.warning("No data for selected time range.")
        return

    # Calculate metrics
    start_value = filtered_df["Value"].iloc[0]
    end_value = filtered_df["Value"].iloc[-1]
    total_return_abs = end_value - start_value
    total_return_pct = ((end_value - start_value) / start_value * 100) if start_value > 0 else 0

    # Calculate benchmark return
    benchmark_return_pct = 0
    if "Benchmark_Price" in filtered_df.columns and filtered_df["Benchmark_Price"].notna().any():
        bench_start = filtered_df["Benchmark_Price"].iloc[0]
        bench_end = filtered_df["Benchmark_Price"].iloc[-1]
        if bench_start > 0:
            benchmark_return_pct = (bench_end - bench_start) / bench_start * 100

    # Calculate annualized IRR
    annualized_irr = calculate_annualized_irr(portfolio_df, selected_range)

    # === HEADER SECTION: Performance vs Market ===
    st.markdown("### Performance vs Market")

    # Top metrics row
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Total Value", value=f"£{total_value:,.0f}", delta=None)
        st.caption(f"{holdings_df['ticker'].nunique() if not holdings_df.empty else '—'} holdings")

    with col2:
        delta_color = "normal" if total_return_abs >= 0 else "inverse"
        st.metric(
            label="Total Returns",
            value=f"£{total_return_abs:,.0f}",
            delta=f"{total_return_pct:+.1f}%",
            delta_color=delta_color,
        )

    with col3:
        st.metric(label="Annualized (IRR)", value=f"{annualized_irr:.1f}%", delta=None)

    st.divider()

    # === CHART SECTION ===
    # Time range selector and performance comparison
    chart_header_col1, chart_header_col2 = st.columns([2, 1])

    with chart_header_col1:
        # Performance comparison labels
        portfolio_color = "#22c55e" if total_return_pct >= 0 else "#ef4444"
        st.markdown(
            f"""
        <div style="display: flex; gap: 2rem; align-items: center;">
            <div>
                <span style="color: {portfolio_color}; font-weight: bold;">— Portfolio</span>
                <span style="color: {portfolio_color}; font-size: 1.2rem; margin-left: 0.5rem;">{total_return_pct:+.1f}%</span>
            </div>
            <div>
                <span style="color: #6b7280;">— VWRL.L</span>
                <span style="color: #6b7280; font-size: 1.2rem; margin-left: 0.5rem;">{benchmark_return_pct:+.1f}%</span>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with chart_header_col2:
        # Time range buttons
        time_ranges = list(TIME_RANGES.keys())
        cols = st.columns(len(time_ranges))
        for i, tr in enumerate(time_ranges):
            with cols[i]:
                btn_type = "primary" if st.session_state.perf_time_range == tr else "secondary"
                if st.button(tr, key=f"tr_{tr}", type=btn_type, use_container_width=True):
                    st.session_state.perf_time_range = tr
                    st.rerun()

    # Create and display the chart
    fig, metrics = create_portfolio_performance_chart(
        portfolio_df, time_range=selected_range, benchmark_name="VWRL.L"
    )

    if fig:
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # === BOTTOM METRICS SECTION ===
    st.markdown("### Returns Breakdown")

    # Calculate unrealized percentage (simplified - all current holdings are unrealized)
    unrealized_pct = total_return_pct if total_return_pct != 0 else 0

    # Bottom metrics row
    met_col1, met_col2, met_col3, met_col4 = st.columns(4)

    with met_col1:
        st.markdown(
            """
        <div style="background: #1e1e2f; padding: 1rem; border-radius: 8px; border-left: 3px solid #22c55e;">
            <div style="color: #9ca3af; font-size: 0.85rem;">Unrealized Returns</div>
            <div style="color: #ffffff; font-size: 1.5rem; font-weight: bold;">£{:,.0f}</div>
            <div style="color: #22c55e; font-size: 0.9rem;">{:.1f}%</div>
        </div>
        """.format(
                total_return_abs if total_return_abs > 0 else 0,
                unrealized_pct if unrealized_pct > 0 else 0,
            ),
            unsafe_allow_html=True,
        )

    with met_col2:
        st.markdown(
            """
        <div style="background: #1e1e2f; padding: 1rem; border-radius: 8px; border-left: 3px solid #3b82f6;">
            <div style="color: #9ca3af; font-size: 0.85rem;">Period High</div>
            <div style="color: #ffffff; font-size: 1.5rem; font-weight: bold;">£{:,.0f}</div>
            <div style="color: #9ca3af; font-size: 0.9rem;">{}</div>
        </div>
        """.format(
                filtered_df["Value"].max(),
                filtered_df.loc[filtered_df["Value"].idxmax(), "Date"].strftime("%b %d, %Y"),
            ),
            unsafe_allow_html=True,
        )

    with met_col3:
        st.markdown(
            """
        <div style="background: #1e1e2f; padding: 1rem; border-radius: 8px; border-left: 3px solid #f59e0b;">
            <div style="color: #9ca3af; font-size: 0.85rem;">Period Low</div>
            <div style="color: #ffffff; font-size: 1.5rem; font-weight: bold;">£{:,.0f}</div>
            <div style="color: #9ca3af; font-size: 0.9rem;">{}</div>
        </div>
        """.format(
                filtered_df["Value"].min(),
                filtered_df.loc[filtered_df["Value"].idxmin(), "Date"].strftime("%b %d, %Y"),
            ),
            unsafe_allow_html=True,
        )

    with met_col4:
        # Calculate volatility
        if len(filtered_df) > 1:
            daily_returns = filtered_df["Value"].pct_change().dropna()
            volatility = daily_returns.std() * np.sqrt(252) * 100  # Annualized
        else:
            volatility = 0

        st.markdown(
            """
        <div style="background: #1e1e2f; padding: 1rem; border-radius: 8px; border-left: 3px solid #8b5cf6;">
            <div style="color: #9ca3af; font-size: 0.85rem;">Volatility (Ann.)</div>
            <div style="color: #ffffff; font-size: 1.5rem; font-weight: bold;">{:.1f}%</div>
            <div style="color: #9ca3af; font-size: 0.9rem;">{} data points</div>
        </div>
        """.format(volatility, len(filtered_df)),
            unsafe_allow_html=True,
        )

    # Outperformance indicator
    if benchmark_return_pct != 0:
        outperformance = total_return_pct - benchmark_return_pct
        outperform_color = "#22c55e" if outperformance >= 0 else "#ef4444"
        outperform_text = "outperforming" if outperformance >= 0 else "underperforming"

        st.markdown(
            f"""
        <div style="margin-top: 1rem; padding: 1rem; background: #1e1e2f; border-radius: 8px; text-align: center;">
            <span style="color: #9ca3af;">Portfolio is </span>
            <span style="color: {outperform_color}; font-weight: bold;">{outperform_text} VWRL.L by {abs(outperformance):.1f}%</span>
            <span style="color: #9ca3af;"> over the selected period</span>
        </div>
        """,
            unsafe_allow_html=True,
        )
