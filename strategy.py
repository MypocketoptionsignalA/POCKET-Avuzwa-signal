import pandas as pd
import pandas_ta as ta

def generate_signal(df: pd.DataFrame):
    if len(df) < 30:
        return None
    
    df = df.copy()
    
    # Indicators
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema9'] = ta.ema(df['close'], length=9)
    df['ema21'] = ta.ema(df['close'], length=21)
    
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Bullish Signal (CALL)
    if (last['ema9'] > last['ema21'] and 
        prev['ema9'] <= prev['ema21'] and 
        last['rsi'] > 50 and 
        last['close'] > last['open']):
        return "BUY"
    
    # Bearish Signal (PUT)
    elif (last['ema9'] < last['ema21'] and 
          prev['ema9'] >= prev['ema21'] and 
          last['rsi'] < 50 and 
          last['close'] < last['open']):
        return "SELL"
    
    return None
