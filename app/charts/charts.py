"""Chart creation functions for portfolio viewer."""

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
