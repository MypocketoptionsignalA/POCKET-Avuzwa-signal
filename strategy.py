def generate_signal(candles):
    if len(candles) < 15:
        return None
    
    last = candles[-1]
    prev = candles[-2]
    
    # Simple Candle Strategy
    if (last['close'] > last['open'] and 
        prev['close'] < prev['open'] and 
        last['close'] > prev['close']):
        return "BUY"
    
    elif (last['close'] < last['open'] and 
          prev['close'] > prev['open'] and 
          last['close'] < prev['close']):
        return "SELL"
    
    return None
