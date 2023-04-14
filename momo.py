import pandas as pd
import numpy as np
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def ema(data, window):
    ema = data.ewm(span=window, adjust=False).mean()
    return ema

def rsi_tradingview(ohlc: pd.DataFrame, period: int = 14, round_rsi: bool = True):
    delta = ohlc["close"].diff()

    up = delta.copy()
    up[up < 0] = 0
    up = pd.Series.ewm(up, alpha=1/period).mean()

    down = delta.copy()
    down[down > 0] = 0
    down *= -1
    down = pd.Series.ewm(down, alpha=1/period).mean()

    rsi = np.where(up == 0, 0, np.where(down == 0, 100, 100 - (100 / (1 + up / down))))

    return np.round(rsi, 2) if round_rsi else rsi

def fetch_data(symbol):
    print(f"Processing {symbol}")
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(endpoint, params=params)
    data = response.json()

    symbol_df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "close_time", "quote_asset_volume", "number_of_trades", "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"])

    symbol_df["timestamp"] = pd.to_datetime(symbol_df["timestamp"], unit="ms")
    symbol_df = symbol_df.set_index("timestamp")

    symbol_df = symbol_df.astype(float)

    symbol_df["EMA4"] = symbol_df["close"].ewm(span=4).mean()
    symbol_df["MA8"] = symbol_df["close"].rolling(8).mean()
    symbol_df["MA20"] = symbol_df["close"].rolling(20).mean()
    symbol_df["MA50"] = symbol_df["close"].rolling(50).mean()

    symbol_df["RSI14"] = rsi_tradingview(symbol_df)

    symbol_df = symbol_df.tail(2)
    symbol_df.index = pd.MultiIndex.from_product([[symbol], symbol_df.index], names=["symbol", "timestamp"])

    return symbol_df

exchange_info_endpoint = "https://api.binance.com/api/v3/exchangeInfo"
endpoint = "https://api.binance.com/api/v3/klines"

exchange_info = requests.get(exchange_info_endpoint).json()
symbol_list = [s["symbol"] for s in exchange_info["symbols"] if s["symbol"].endswith("USDT")]

interval = "1h"
limit = 100

max_threads = 10
data_list = []

with ThreadPoolExecutor(max_workers=max_threads) as executor:
    futures = [executor.submit(fetch_data, symbol) for symbol in symbol_list]

    for future in as_completed(futures):
        symbol_df = future.result()
        data_list.append(symbol_df)

data_df = pd.concat(data_list, axis=0)

data_df.to_excel("crypto_data.xlsx")

FOD_list = []
FOB_list = []
for symbol in symbol_list:
    
    rows = data_df.loc[symbol]
    prev = rows.iloc[-2]
    cur = rows.iloc[-1]
    close = rows.iloc[-1].close
    prevema4 = prev.EMA4
    curema4 = cur.EMA4
    prevma8 = prev.MA8
    curma8 = cur.MA8
    prevma20 = prev.MA20
    curma20 = cur.MA20
    prevma50 = prev.MA50
    curma50 = cur.MA50
    rsi14 = cur.RSI14

    ema4x8cross = prevema4 < prevma8 and curema4 > curma8 
    strongtrend = curma8 > curma20 > curma50 
    retracetrend = curma20 > curma8 > curma50
    if ema4x8cross:
        if strongtrend and rsi14>=60:
            FOD_list.append(symbol)
        elif retracetrend and rsi14>=50:
            FOB_list.append(symbol)

print("FOB LIST:")
print(FOB_list)
print("FOD LIST:")
print(FOD_list)