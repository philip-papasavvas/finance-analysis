"""Chart creation functions for portfolio viewer."""

from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go


# Currency symbol mapping for tickers
TICKER_CURRENCY_MAP = {
    "BRK-B": "$",
    "EMIM.L": "p",
    "GB00B2PLJD73": "£",
    "GB00BD6PG787": "£",
    "GB00BF0TZG22": "p",
    "LU1033663649": "£",
    "MWOT.DE": "€",
    "NVDA": "$",
    "VERG.L": "£",
    "VUAG.L": "£",
    "VWRP.L": "£",
}


def create_timeline_chart(df: pd.DataFrame, fund_name: str) -> go.Figure:
    """Create a bar chart of buy/sell transactions with positive/negative bars."""
    if df.empty:
        return None

    # Convert date to datetime
    df_chart = df.copy()
    df_chart["Date"] = pd.to_datetime(df_chart["Date"])
    df_chart = df_chart.sort_values("Date")

    # Create bar values (positive for buys, negative for sells)
    df_chart["Bar Value"] = df_chart.apply(
        lambda row: row["Units"] if row["Type"] == "BUY" else -row["Units"], axis=1
    )

    # Determine colors (green for buys, red for sells)
    colors = ["green" if val > 0 else "red" for val in df_chart["Bar Value"]]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df_chart["Date"],
            y=df_chart["Bar Value"],
            marker=dict(color=colors),
            name="Transactions",
            hovertemplate="<b>%{customdata}</b><br>Date: %{x|%Y-%m-%d}<br>Units: %{y:.2f}<extra></extra>",
            customdata=df_chart["Type"],
        )
    )

    # Add a horizontal line at y=0
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)

    # Update layout
    fig.update_layout(
        title=f"Buy/Sell Transactions - {fund_name}",
        xaxis_title="Date",
        yaxis_title="Units (Green = Buy, Red = Sell)",
        hovermode="x unified",
        height=400,
        template="plotly_white",
        showlegend=False,
    )

    return fig


def create_cumulative_units_chart(df: pd.DataFrame, fund_name: str) -> go.Figure:
    """Create a chart showing cumulative units over time."""
    if df.empty:
        return None

    # Convert date to datetime
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    # Calculate cumulative units (buys are positive, sells are negative)
    df["Cumulative Units"] = df["Units"].where(df["Type"] == "BUY", -df["Units"]).cumsum()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Cumulative Units"],
            fill="tozeroy",
            name="Cumulative Units",
            line=dict(color="blue", width=2),
            hovertemplate="<b>Cumulative Units</b><br>Date: %{x|%Y-%m-%d}<br>Units: %{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=f"Cumulative Units Over Time - {fund_name}",
        xaxis_title="Date",
        yaxis_title="Units Held",
        hovermode="x unified",
        height=400,
        template="plotly_white",
    )

    return fig


def create_price_chart(
    df: pd.DataFrame, ticker: str, fund_name: str, transactions_df: pd.DataFrame = None
) -> go.Figure:
    """Create a line chart for price history with optional buy/sell transaction markers."""
    if df.empty:
        return None

    # Determine currency symbol based on ticker
    currency_symbol = TICKER_CURRENCY_MAP.get(ticker, "£")

    fig = go.Figure()

    # Price line
    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["Price"],
            fill="tozeroy",
            name="Price",
            line=dict(color="green", width=2),
            hovertemplate=f"<b>Price</b><br>Date: %{{x|%Y-%m-%d}}<br>Price: {currency_symbol}%{{y:.2f}}<extra></extra>",
        )
    )

    # Add buy/sell markers if transactions data provided
    if transactions_df is not None and not transactions_df.empty:
        # Buy markers (dark green circles)
        buy_df = transactions_df[transactions_df["Type"] == "BUY"]
        if not buy_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=buy_df["Date"],
                    y=buy_df["Marker_Y"],
                    mode="markers",
                    name="BUY",
                    marker=dict(
                        color="darkgreen",
                        size=10,
                        symbol="circle",
                        line=dict(color="white", width=1),
                    ),
                    hovertemplate=(
                        "<b>BUY</b><br>"
                        "Date: %{x|%Y-%m-%d}<br>"
                        "Units: %{customdata[0]:.2f}<br>"
                        "Price: £%{customdata[1]:.2f}<br>"
                        "Value: £%{customdata[2]:,.2f}"
                        "<extra></extra>"
                    ),
                    customdata=buy_df[["Units", "Price", "Value"]].values,
                )
            )

        # Sell markers (dark red circles)
        sell_df = transactions_df[transactions_df["Type"] == "SELL"]
        if not sell_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=sell_df["Date"],
                    y=sell_df["Marker_Y"],
                    mode="markers",
                    name="SELL",
                    marker=dict(
                        color="darkred", size=10, symbol="circle", line=dict(color="white", width=1)
                    ),
                    hovertemplate=(
                        "<b>SELL</b><br>"
                        "Date: %{x|%Y-%m-%d}<br>"
                        "Units: %{customdata[0]:.2f}<br>"
                        "Price: £%{customdata[1]:.2f}<br>"
                        "Value: £%{customdata[2]:,.2f}"
                        "<extra></extra>"
                    ),
                    customdata=sell_df[["Units", "Price", "Value"]].values,
                )
            )

    fig.update_layout(
        title=f"Price History - {fund_name} ({ticker})",
        xaxis_title="Date",
        yaxis_title="Price (£)",
        hovermode="closest",
        height=500,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


# Time range definitions for portfolio performance chart
TIME_RANGES = {
    "7D": timedelta(days=7),
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "YTD": "ytd",  # Special handling for year-to-date
    "1Y": timedelta(days=365),
    "ALL": None,  # No filter, show all data
}


def filter_dataframe_by_time_range(
    df: pd.DataFrame, time_range: str, date_column: str = "Date"
) -> pd.DataFrame:
    """Filter dataframe by time range.

    Args:
        df: DataFrame with a date column
        time_range: One of "7D", "1M", "3M", "YTD", "1Y", "ALL"
        date_column: Name of the date column

    Returns:
        Filtered DataFrame
    """
    if df.empty or time_range == "ALL":
        return df

    # Ensure date column is datetime
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])

    today = datetime.now()

    if time_range == "YTD":
        # Year to date: from Jan 1 of current year
        start_date = datetime(today.year, 1, 1)
    else:
        delta = TIME_RANGES.get(time_range)
        if delta is None:
            return df
        start_date = today - delta

    return df[df[date_column] >= start_date]


def create_portfolio_performance_chart(
    df: pd.DataFrame, time_range: str = "1Y", benchmark_name: str = "VWRL.L"
) -> tuple[go.Figure, dict]:
    """Create a percentage returns chart comparing portfolio vs benchmark.

    Args:
        df: DataFrame with Date, Value, and optionally Benchmark_Price columns
        time_range: Time range filter ("7D", "1M", "3M", "YTD", "1Y", "ALL")
        benchmark_name: Name to display for benchmark

    Returns:
        Tuple of (Plotly figure, metrics dict)
    """
    if df.empty:
        return None, {}

    # Filter by time range
    filtered_df = filter_dataframe_by_time_range(df, time_range).copy()

    if filtered_df.empty or len(filtered_df) < 2:
        return None, {}

    # Calculate percentage returns from period start
    start_value = filtered_df["Value"].iloc[0]
    filtered_df["Portfolio_Return"] = ((filtered_df["Value"] - start_value) / start_value) * 100

    # Calculate benchmark returns if available
    has_benchmark = (
        "Benchmark_Price" in filtered_df.columns and filtered_df["Benchmark_Price"].notna().any()
    )
    if has_benchmark:
        benchmark_start = filtered_df["Benchmark_Price"].iloc[0]
        if benchmark_start > 0:
            filtered_df["Benchmark_Return"] = (
                (filtered_df["Benchmark_Price"] - benchmark_start) / benchmark_start
            ) * 100
        else:
            has_benchmark = False

    # Get final values for metrics
    end_value = filtered_df["Value"].iloc[-1]
    portfolio_return = filtered_df["Portfolio_Return"].iloc[-1]
    benchmark_return = filtered_df["Benchmark_Return"].iloc[-1] if has_benchmark else 0

    # Determine colors
    portfolio_color = "#22c55e" if portfolio_return >= 0 else "#ef4444"  # Green/Red
    benchmark_color = "#6b7280"  # Gray

    # Create figure with dark theme styling
    fig = go.Figure()

    # Add benchmark line first (so it's behind portfolio)
    if has_benchmark:
        fig.add_trace(
            go.Scatter(
                x=filtered_df["Date"],
                y=filtered_df["Benchmark_Return"],
                name=benchmark_name,
                line=dict(color=benchmark_color, width=2),
                hovertemplate=(
                    f"<b>{benchmark_name}</b><br>"
                    "Date: %{x|%b %d, %Y}<br>"
                    "Return: %{y:.1f}%"
                    "<extra></extra>"
                ),
            )
        )

    # Add portfolio line
    fig.add_trace(
        go.Scatter(
            x=filtered_df["Date"],
            y=filtered_df["Portfolio_Return"],
            name="Portfolio",
            line=dict(color=portfolio_color, width=2.5),
            fill="tozeroy",
            fillcolor=f"rgba({34 if portfolio_return >= 0 else 239}, {197 if portfolio_return >= 0 else 68}, {94 if portfolio_return >= 0 else 68}, 0.1)",
            hovertemplate=(
                "<b>Portfolio</b><br>"
                "Date: %{x|%b %d, %Y}<br>"
                "Return: %{y:.1f}%"
                "<extra></extra>"
            ),
        )
    )

    # Add zero line
    fig.add_hline(y=0, line_dash="dot", line_color="#4b5563", line_width=1)

    # Update layout for dark/polished look
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#1a1a2e",
        plot_bgcolor="#1a1a2e",
        height=350,
        margin=dict(l=20, r=20, t=30, b=20),
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12),
        ),
        xaxis=dict(
            showgrid=False,
            showline=False,
            tickformat="%b",
            tickfont=dict(color="#9ca3af"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#2d2d44",
            showline=False,
            ticksuffix="%",
            tickfont=dict(color="#9ca3af"),
            zeroline=False,
        ),
    )

    # Calculate metrics for display
    metrics = {
        "current_value": end_value,
        "start_value": start_value,
        "total_return_pct": portfolio_return,
        "total_return_abs": end_value - start_value,
        "benchmark_return_pct": benchmark_return if has_benchmark else None,
        "period_high": filtered_df["Value"].max(),
        "period_low": filtered_df["Value"].min(),
    }

    return fig, metrics
