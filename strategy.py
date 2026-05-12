def generate_signal(candles):
    if len(candles) < 20:
        return None
    
    # Last 3 candles
    last = candles[-1]
    prev = candles[-2]
    
    # Simple logic: Green candle after red + higher close
    if (last['close'] > last['open'] and 
        prev['close'] < prev['open'] and 
        last['close'] > prev['close']):
        return "BUY"
    
    elif (last['close'] < last['open'] and 
          prev['close'] > prev['open'] and 
          last['close'] < prev['close']):
        return "SELL"
    
    return None
