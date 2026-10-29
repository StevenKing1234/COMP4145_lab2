# COMP4145 Lab 2: MSFT Golden Cross

Downloads five years of daily Microsoft stock data, backtests a 50-day/200-day
golden-cross strategy, and displays the results in a Streamlit dashboard.

## Run locally

Install the requirements and launch the dashboard:

```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

The dashboard reads `msft_5y_daily.csv` and
`msft_golden_cross_trades.csv`. To refresh them from Yahoo Finance, run:

```bash
python trading_strategy.py
```

The strategy enters at the close when the 50-day moving average crosses above
the 200-day moving average. It exits when the closing price reaches 15% above
the entry price or at the close of the 60th following trading session.
