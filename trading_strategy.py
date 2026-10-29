"""Download Microsoft daily prices and backtest a 50/200-day golden cross."""

import argparse
from pathlib import Path

import pandas as pd
import yfinance as yf


def download_market_data(
	ticker: str = "MSFT",
	period: str = "5y",
	interval: str = "1d",
) -> pd.DataFrame:
	"""Download daily OHLCV data from Yahoo Finance."""
	data = yf.download(
		tickers=ticker,
		period=period,
		interval=interval,
		auto_adjust=False,
		progress=False,
		threads=False,
	)
	if data.empty:
		raise RuntimeError(f"Yahoo Finance returned no data for {ticker}.")

	if isinstance(data.columns, pd.MultiIndex):
		for level in range(data.columns.nlevels):
			if ticker in data.columns.get_level_values(level):
				data.columns = data.columns.droplevel(level)
				break
		if isinstance(data.columns, pd.MultiIndex):
			data.columns = [" ".join(map(str, column)).strip() for column in data.columns]

	data.index.name = "Date"
	return data.reset_index()


def backtest_golden_cross(
	data: pd.DataFrame,
	take_profit: float = 0.15,
	max_holding_days: int = 60,
) -> tuple[pd.DataFrame, pd.DataFrame]:
	"""Add moving averages and return the daily data and simulated trades.

	A buy is made at the close on the first day the 50-day average crosses
	above the 200-day average. The position exits at a close at least 15%
	above the entry price, or at the close of the 60th following session.
	A position that has not reached either exit by the end of the data remains
	open in the trades output.
	"""
	if "Close" not in data.columns:
		raise ValueError("Input data must contain a 'Close' column.")
	if take_profit <= 0 or max_holding_days < 1:
		raise ValueError("take_profit must be positive and max_holding_days at least 1.")

	result = data.copy().reset_index(drop=True)
	result["MA_50"] = result["Close"].rolling(50, min_periods=50).mean()
	result["MA_200"] = result["Close"].rolling(200, min_periods=200).mean()
	above_slow_average = result["MA_50"] > result["MA_200"]
	result["Buy_Signal"] = (
		above_slow_average & ~above_slow_average.shift(1, fill_value=False)
	)

	trades: list[dict[str, object]] = []
	index = 0
	while index < len(result):
		if not result.at[index, "Buy_Signal"]:
			index += 1
			continue

		buy_price = float(result.at[index, "Close"])
		buy_date = result.at[index, "Date"] if "Date" in result.columns else index
		target_price = buy_price * (1 + take_profit)
		deadline = index + max_holding_days
		last_available = min(deadline, len(result) - 1)
		sell_index = None
		exit_reason = "open"

		for candidate in range(index + 1, last_available + 1):
			if float(result.at[candidate, "Close"]) >= target_price:
				sell_index = candidate
				exit_reason = "take_profit"
				break
			if candidate == deadline:
				sell_index = candidate
				exit_reason = "time_limit"
				break

		if sell_index is None:
			trades.append(
				{
					"Buy_Date": buy_date,
					"Buy_Price": buy_price,
					"Target_Price": target_price,
					"Sell_Date": None,
					"Sell_Price": None,
					"Return_Pct": None,
					"Exit_Reason": exit_reason,
				}
			)
			break

		sell_price = float(result.at[sell_index, "Close"])
		sell_date = result.at[sell_index, "Date"] if "Date" in result.columns else sell_index
		trades.append(
			{
				"Buy_Date": buy_date,
				"Buy_Price": buy_price,
				"Target_Price": target_price,
				"Sell_Date": sell_date,
				"Sell_Price": sell_price,
				"Return_Pct": (sell_price / buy_price - 1) * 100,
				"Exit_Reason": exit_reason,
			}
		)
		index = sell_index + 1

	trade_columns = [
		"Buy_Date",
		"Buy_Price",
		"Target_Price",
		"Sell_Date",
		"Sell_Price",
		"Return_Pct",
		"Exit_Reason",
	]
	return result, pd.DataFrame(trades, columns=trade_columns)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--ticker", default="MSFT", help="Yahoo Finance ticker (default: MSFT)")
	parser.add_argument("--period", default="5y", help="History period (default: 5y)")
	parser.add_argument("--interval", default="1d", help="Price interval (default: 1d)")
	parser.add_argument(
		"--data-output",
		type=Path,
		default=Path("msft_5y_daily.csv"),
		help="Destination for daily prices and moving averages",
	)
	parser.add_argument(
		"--trades-output",
		type=Path,
		default=Path("msft_golden_cross_trades.csv"),
		help="Destination for simulated trades",
	)
	args = parser.parse_args()

	try:
		market_data = download_market_data(args.ticker, args.period, args.interval)
		daily_data, trades = backtest_golden_cross(market_data)
		args.data_output.parent.mkdir(parents=True, exist_ok=True)
		args.trades_output.parent.mkdir(parents=True, exist_ok=True)
		daily_data.to_csv(args.data_output, index=False)
		trades.to_csv(args.trades_output, index=False)
	except Exception as error:
		parser.exit(1, f"Download or backtest failed: {error}\n")

	closed_trades = trades[trades["Sell_Price"].notna()]
	print(f"Saved {len(daily_data)} daily rows to {args.data_output}")
	print(f"Saved {len(trades)} trades ({len(closed_trades)} closed) to {args.trades_output}")


if __name__ == "__main__":
	main()
