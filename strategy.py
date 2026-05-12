def generate_signal(candles):
    if len(candles) < 10:
        return None
    
    last = candles[-1]
    prev = candles[-2]
    
    # Basic Candle Pattern Strategy
    bullish = (last['close'] > last['open'] and 
               prev['close'] < prev['open'] and 
               last['close'] > prev['close'])
    
    bearish = (last['close'] < last['open'] and 
               prev['close'] > prev['open'] and 
               last['close'] < prev['close'])
    
    if bullish:
        return "BUY"
    elif bearish:
        return "SELL"
    
    return None
