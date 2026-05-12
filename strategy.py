def generate_signal(candles):
    if len(candles) < 8:
        return None
    
    last = candles[-1]
    prev = candles[-2]
    
    # More sensitive strategy for OTC
    if (last.get('close', 0) > last.get('open', 0) and 
        prev.get('close', 0) < prev.get('open', 0)):
        return "BUY"
    
    elif (last.get('close', 0) < last.get('open', 0) and 
          prev.get('close', 0) > prev.get('open', 0)):
        return "SELL"
    
    return None
