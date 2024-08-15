import ccxt
import pandas as pd
from datetime import datetime, timedelta
import json

def log(message):
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")

def fetch_ohlcv_data(exchange, symbol, timeframe, limit=100):
    log(f"Fetching {timeframe} data for {symbol}...")
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df['timestamp'] = df['timestamp'].dt.tz_convert('America/New_York')
        log(f"Fetched {len(df)} candles for {symbol} {timeframe}")
        return df
    except Exception as e:
        log(f"Error fetching data for {symbol} {timeframe}: {str(e)}")
        return None

def find_bullish_fvg(df):
    fvgs = []
    for i in range(2, len(df)):
        if df.iloc[i]['low'] > df.iloc[i-2]['high']:
            fvg = {
                'start_time': df.iloc[i-2]['timestamp'],
                'mid_time': df.iloc[i-1]['timestamp'],
                'end_time': df.iloc[i]['timestamp'],
                'high': df.iloc[i-2]['high'],
                'low': df.iloc[i]['low'],
                'type': 'bullish'
            }
            fvgs.append(fvg)
    return fvgs

def find_bearish_fvg(df):
    fvgs = []
    for i in range(2, len(df)):
        if df.iloc[i]['high'] < df.iloc[i-2]['low']:
            fvg = {
                'start_time': df.iloc[i-2]['timestamp'],
                'mid_time': df.iloc[i-1]['timestamp'],
                'end_time': df.iloc[i]['timestamp'],
                'high': df.iloc[i-2]['low'],
                'low': df.iloc[i]['high'],
                'type': 'bearish'
            }
            fvgs.append(fvg)
    return fvgs

def analyze_fvgs(exchange, symbol):
    log(f"Analyzing FVGs for {symbol}...")
    timeframes = {'2h': 120, '1h': 60, '30m': 30, '15m': 15}
    fvgs = {}
    
    for tf in timeframes:
        df = fetch_ohlcv_data(exchange, symbol, tf)
        if df is not None:
            fvgs[tf] = find_bullish_fvg(df) + find_bearish_fvg(df)
            log(f"Found {len(fvgs[tf])} FVGs for {symbol} {tf} timeframe")
        else:
            log(f"Skipping FVG analysis for {symbol} {tf} due to data fetch error")
    
    return fvgs

def get_top_coins(exchange, quote_currency='USDT', limit=10):
    log("Fetching top USDT pairs by volume...")
    try:
        tickers = exchange.fetch_tickers()
        usdt_pairs = {symbol: data for symbol, data in tickers.items() if symbol.endswith(quote_currency)}
        sorted_pairs = sorted(usdt_pairs.items(), key=lambda x: x[1]['quoteVolume'], reverse=True)
        top_coins = [pair[0] for pair in sorted_pairs[:limit]]
        log(f"Top {limit} USDT pairs: {top_coins}")
        return top_coins
    except Exception as e:
        log(f"Error fetching top coins: {str(e)}")
        return []

def find_overlapping_fvgs(fvgs):
    overlapping_fvgs = {}
    
    # Check for (2h, 1h, 30m) overlap
    for fvg_2h in fvgs['2h']:
        for fvg_1h in fvgs['1h']:
            if fvg_1h['start_time'] >= fvg_2h['start_time'] and fvg_1h['end_time'] <= fvg_2h['end_time']:
                for fvg_30m in fvgs['30m']:
                    if (fvg_30m['start_time'] >= fvg_1h['start_time'] and 
                        fvg_30m['end_time'] <= fvg_1h['end_time'] and
                        fvg_2h['type'] == fvg_1h['type'] == fvg_30m['type']):
                        key = (fvg_1h['start_time'].isoformat(), fvg_1h['end_time'].isoformat(), '2h, 1h, 30m', fvg_2h['type'])
                        if key not in overlapping_fvgs:
                            overlapping_fvgs[key] = {
                                'start_time': fvg_1h['start_time'].isoformat(),
                                'end_time': fvg_1h['end_time'].isoformat(),
                                'timeframes': '2h, 1h, 30m',
                                'fvgs': {
                                    '2h': [fvg_2h],
                                    '1h': [fvg_1h],
                                    '30m': [fvg_30m]
                                },
                                'type': fvg_2h['type']
                            }
    
    # Check for (1h, 30m, 15m) overlap
    for fvg_1h in fvgs['1h']:
        for fvg_30m in fvgs['30m']:
            if (fvg_30m['start_time'] >= fvg_1h['start_time'] and 
                fvg_30m['end_time'] <= fvg_1h['end_time'] and
                fvg_30m['start_time'].minute == 0):  # Ensure 30m FVG starts at the hour
                for fvg_15m in fvgs['15m']:
                    if (fvg_15m['start_time'] >= fvg_30m['start_time'] and 
                        fvg_15m['end_time'] <= fvg_30m['end_time'] and
                        fvg_15m['start_time'].minute == 0 and  # Ensure 15m FVG starts at the hour
                        fvg_1h['type'] == fvg_30m['type'] == fvg_15m['type']):
                        key = (fvg_1h['start_time'].isoformat(), fvg_1h['end_time'].isoformat(), '1h, 30m, 15m', fvg_1h['type'])
                        if key not in overlapping_fvgs:
                            overlapping_fvgs[key] = {
                                'start_time': fvg_1h['start_time'].isoformat(),
                                'end_time': fvg_1h['end_time'].isoformat(),
                                'timeframes': '1h, 30m, 15m',
                                'fvgs': {
                                    '1h': [fvg_1h],
                                    '30m': [fvg_30m],
                                    '15m': [fvg_15m]
                                },
                                'type': fvg_1h['type']
                            }
    
    return list(overlapping_fvgs.values())

def main():
    log("Initializing exchange...")
    exchange = ccxt.binance()
    
    top_coins = get_top_coins(exchange)
    if not top_coins:
        log("Failed to fetch top coins. Exiting.")
        return

    all_fvgs = []
    
    for symbol in top_coins:
        log(f"\nAnalyzing {symbol}...")
        fvgs = analyze_fvgs(exchange, symbol)
        
        log(f"Finding overlapping FVGs for {symbol}...")
        overlapping_fvgs = find_overlapping_fvgs(fvgs)
        
        for fvg in overlapping_fvgs:
            fvg['symbol'] = symbol
        
        all_fvgs.extend(overlapping_fvgs)
    
    log("\nWriting data to JSON file...")
    with open('fvg_data.json', 'w') as f:
        json.dump(all_fvgs, f, indent=2, default=str)
    log("Data written to fvg_data.json")

    log(f"\nAnalysis complete. Total overlapping FVGs found: {len(all_fvgs)}")

if __name__ == "__main__":
    main()