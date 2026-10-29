"""Streamlit dashboard for the MSFT golden-cross backtest."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
DAILY_FILE = ROOT / "msft_5y_daily.csv"
TRADES_FILE = ROOT / "msft_golden_cross_trades.csv"

st.set_page_config(
    page_title="MSFT | Golden Cross",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {
      --ink: #172a26;
      --muted: #64736e;
      --green: #167c62;
      --lime: #d7ed76;
      --coral: #d9664f;
      --paper: #f4f7f3;
      --line: #dce5df;
    }
    html, body, [class*="css"] {
      font-family: 'Manrope', sans-serif;
      color: var(--ink);
    }
    .stApp {
      background: linear-gradient(155deg, #f8faf7 0%, #edf4ef 52%, #f5f4ed 100%);
    }
    .block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 3rem; }
    [data-testid="stHeader"] { background: transparent; }
    h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
    h1 { font-size: 2rem !important; font-weight: 800 !important; }
    h2 { font-size: 1.25rem !important; font-weight: 700 !important; }
    .eyebrow {
      color: var(--green); font-family: 'DM Mono', monospace; font-size: .73rem;
      font-weight: 500; text-transform: uppercase; letter-spacing: 0;
    }
    .subhead { color: var(--muted); font-size: .92rem; margin-top: -.45rem; }
    [data-testid="stMetric"] {
      background: rgba(255,255,255,.82); border: 1px solid var(--line);
      border-radius: 6px; padding: 1rem 1.1rem;
    }
    [data-testid="stMetricLabel"] { color: var(--muted); font-size: .78rem; }
    [data-testid="stMetricValue"] { color: var(--ink); font-weight: 700; }
    [data-testid="stTabs"] [role="tablist"] {
      gap: .35rem; border-bottom: 1px solid var(--line);
    }
    [data-testid="stTabs"] button[role="tab"] {
      color: var(--muted); font-weight: 700; padding: .8rem 1rem;
    }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
      color: var(--green); border-bottom-color: var(--green);
    }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 6px; }
    .note { color: var(--muted); font-size: .82rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data

def load_results() -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = pd.read_csv(DAILY_FILE, parse_dates=["Date"])
    trades = pd.read_csv(TRADES_FILE, parse_dates=["Buy_Date", "Sell_Date"])
    return daily, trades


if not DAILY_FILE.exists() or not TRADES_FILE.exists():
    st.error("Backtest results are missing. Run `python trading_strategy.py` first.")
    st.stop()

try:
    daily_data, trades = load_results()
except Exception as error:
    st.error(f"Could not read the backtest CSV files: {error}")
    st.stop()

closed = trades[trades["Sell_Price"].notna()].copy()
open_trades = trades[trades["Sell_Price"].isna()].copy()
returns = pd.to_numeric(closed["Return_Pct"], errors="coerce").dropna()
winners = int((returns > 0).sum())
losers = int((returns <= 0).sum())
win_rate = (winners / len(returns) * 100) if len(returns) else 0.0
compounded_return = ((1 + returns / 100).prod() - 1) * 100 if len(returns) else 0.0

latest_close = float(daily_data["Close"].iloc[-1])
latest_date = daily_data["Date"].iloc[-1]
first_date = daily_data["Date"].iloc[0]

st.markdown('<div class="eyebrow">MARKET STUDY / 01</div>', unsafe_allow_html=True)
st.title("Microsoft · Golden Cross")
st.markdown(
    f'<div class="subhead">MSFT · 50-day / 200-day moving averages · '
    f'{first_date:%b %d, %Y} — {latest_date:%b %d, %Y}</div>',
    unsafe_allow_html=True,
)
st.write("")

chart_tab, stats_tab, detail_tab = st.tabs(
    ["Price chart", "Trade statistics", "Trade details"]
)

with chart_tab:
    left, right = st.columns([3, 1])
    with left:
        st.subheader("Daily closing price")
    with right:
        st.metric("Latest close", f"${latest_close:,.2f}", f"{latest_date:%b %d, %Y}")

    chart = go.Figure()
    chart.add_trace(
        go.Scatter(
            x=daily_data["Date"], y=daily_data["Close"], name="Close",
            mode="lines", line={"color": "#172a26", "width": 1.8},
            hovertemplate="%{x|%b %d, %Y}<br>Close $%{y:,.2f}<extra></extra>",
        )
    )
    chart.add_trace(
        go.Scatter(
            x=daily_data["Date"], y=daily_data["MA_50"], name="50-day MA",
            mode="lines", line={"color": "#167c62", "width": 1.5},
            hovertemplate="%{x|%b %d, %Y}<br>50-day MA $%{y:,.2f}<extra></extra>",
        )
    )
    chart.add_trace(
        go.Scatter(
            x=daily_data["Date"], y=daily_data["MA_200"], name="200-day MA",
            mode="lines", line={"color": "#d19a2a", "width": 1.5},
            hovertemplate="%{x|%b %d, %Y}<br>200-day MA $%{y:,.2f}<extra></extra>",
        )
    )
    if not trades.empty:
        chart.add_trace(
            go.Scatter(
                x=trades["Buy_Date"], y=trades["Buy_Price"], name="Buy",
                mode="markers", marker={"symbol": "circle", "size": 10, "color": "#167c62", "line": {"color": "white", "width": 1.5}},
                customdata=trades["Buy_Price"],
                hovertemplate="BUY · %{x|%b %d, %Y}<br>Price $%{customdata:,.2f}<extra></extra>",
            )
        )
        if not closed.empty:
            chart.add_trace(
                go.Scatter(
                    x=closed["Sell_Date"], y=closed["Sell_Price"], name="Sell",
                    mode="markers", marker={"symbol": "x", "size": 10, "color": "#d9664f", "line": {"width": 2}},
                    customdata=closed["Sell_Price"],
                    hovertemplate="SELL · %{x|%b %d, %Y}<br>Price $%{customdata:,.2f}<extra></extra>",
                )
            )

    chart.update_layout(
        template="plotly_white", height=530, margin={"l": 8, "r": 16, "t": 20, "b": 12},
        hovermode="x unified", paper_bgcolor="rgba(255,255,255,0.82)",
        plot_bgcolor="rgba(255,255,255,0.82)", font={"family": "Manrope, sans-serif", "color": "#172a26"},
        legend={"orientation": "h", "y": 1.08, "x": 0},
        xaxis={"title": None, "showgrid": False, "rangeselector": {"buttons": [
            {"count": 6, "label": "6M", "step": "month", "stepmode": "backward"},
            {"count": 1, "label": "1Y", "step": "year", "stepmode": "backward"},
            {"label": "All", "step": "all"},
        ]}},
        yaxis={"title": None, "tickprefix": "$", "tickformat": ",.0f", "gridcolor": "#e8eeea"},
    )
    st.plotly_chart(chart, use_container_width=True, config={"displaylogo": False})
    st.markdown(
        '<div class="note">Green circles mark entries; coral crosses mark completed exits. '
        'Price and trade levels use daily closing prices.</div>',
        unsafe_allow_html=True,
    )

with stats_tab:
    st.subheader("Strategy results")
    st.markdown('<div class="subhead">Closed trades only are used for return and win-rate calculations.</div>', unsafe_allow_html=True)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Total trades", f"{len(trades)}", f"{len(open_trades)} open")
    metric_columns[1].metric("Win rate", f"{win_rate:.1f}%", f"{winners} wins · {losers} losses")
    metric_columns[2].metric("Compounded return", f"{compounded_return:+.2f}%", "equal capital per sequential trade")
    average_return = returns.mean() if len(returns) else 0.0
    metric_columns[3].metric("Average trade", f"{average_return:+.2f}%", "closed trades")

    st.write("")
    result_columns = st.columns(3)
    best_return = returns.max() if len(returns) else 0.0
    worst_return = returns.min() if len(returns) else 0.0
    result_columns[0].metric("Best closed trade", f"{best_return:+.2f}%")
    result_columns[1].metric("Worst closed trade", f"{worst_return:+.2f}%")
    result_columns[2].metric("Current position", "Open" if len(open_trades) else "None")

    st.write("")
    st.caption(
        "Compounded return assumes each completed trade reinvests the full balance in sequence; "
        "it excludes fees, taxes, and slippage."
    )
    if len(open_trades):
        for _, trade in open_trades.iterrows():
            st.info(
                f"Open position since {trade['Buy_Date']:%b %d, %Y} at "
                f"\\${trade['Buy_Price']:,.2f}; target \\${trade['Target_Price']:,.2f}."
            )

with detail_tab:
    st.subheader("Trade ledger")
    if trades.empty:
        st.info("No golden-cross entries were found in this period.")
    else:
        display = trades.copy()
        display["Status"] = display["Sell_Price"].apply(lambda price: "Open" if pd.isna(price) else "Closed")
        display["Return_Pct"] = pd.to_numeric(display["Return_Pct"], errors="coerce")
        display = display.rename(
            columns={
                "Buy_Date": "Buy date", "Buy_Price": "Buy price", "Target_Price": "15% target",
                "Sell_Date": "Sell date", "Sell_Price": "Sell price", "Return_Pct": "Return (%)",
                "Exit_Reason": "Exit reason",
            }
        )
        display = display[[
            "Status", "Buy date", "Buy price", "15% target", "Sell date", "Sell price", "Return (%)", "Exit reason"
        ]]
        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Status"),
                "Buy date": st.column_config.DateColumn("Buy date", format="MMM D, YYYY"),
                "Sell date": st.column_config.DateColumn("Sell date", format="MMM D, YYYY"),
                "Buy price": st.column_config.NumberColumn("Buy price", format="$%.2f"),
                "15% target": st.column_config.NumberColumn("15% target", format="$%.2f"),
                "Sell price": st.column_config.NumberColumn("Sell price", format="$%.2f"),
                "Return (%)": st.column_config.NumberColumn("Return (%)", format="%.2f%%"),
                "Exit reason": st.column_config.TextColumn("Exit reason"),
            },
        )
        st.download_button(
            "Download trade ledger",
            data=trades.to_csv(index=False).encode("utf-8"),
            file_name="msft_golden_cross_trades.csv",
            mime="text/csv",
        )
