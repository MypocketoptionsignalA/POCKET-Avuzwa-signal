import os
import time
import ccxt
import pandas as pd
import numpy as np
from telegram import Bot
from datetime import datetime

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("ADMIN_USER_ID")  # you become the receiver
USER_SSID = os.getenv("USER_SSID")


TIMEFRAME = "1m"
LIMIT = 100
COOLDOWN = 180

# OTC mapping (proxy data)
OTC_PAIRS = {
    "EUR/USD OTC": "BTC/USDT",
    "GBP/USD OTC": "ETH/USDT",
    "USD/JPY OTC": "BNB/USDT",
    "AUD/USD OTC": "SOL/USDT"
}

bot = Bot(token=TOKEN)
exchange = ccxt.binance()

last_signal_time = 0

wins = 0
losses = 0
losing_streak = 0

# === INDICATORS ===
def calculate_ao(df):
    median = (df['high'] + df['low']) / 2
    return median.rolling(5).mean() - median.rolling(34).mean()

def calculate_cci(df, period=20):
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
    return (tp - sma) / (0.015 * mad)

def detect_fractal(df):
    if len(df) < 5:
        return None

    if df['low'].iloc[-3] < df['low'].iloc[-4] and df['low'].iloc[-3] < df['low'].iloc[-2]:
        return "bullish"

    if df['high'].iloc[-3] > df['high'].iloc[-4] and df['high'].iloc[-3] > df['high'].iloc[-2]:
        return "bearish"

    return None

# === SESSION FILTER (SA TIME) ===
def valid_session():
    hour = datetime.utcnow().hour + 2
    return 9 <= hour <= 18

# === DATA ===
def get_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT)
    return pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])

# === SIGNAL STRENGTH ===
def signal_strength(ao, cci):
    score = 0
    if abs(ao.iloc[-1]) > abs(ao.iloc[-2]):
        score += 1
    if abs(cci.iloc[-1]) > 120:
        score += 1
    return "HIGH" if score == 2 else "MEDIUM"

# === SIGNAL LOGIC ===
def check_signal(df):
    ao = calculate_ao(df)
    cci = calculate_cci(df)
    fractal = detect_fractal(df)

    candles = df.tail(3)

    # BUY
    if (ao.iloc[-1] > 0 and ao.iloc[-1] > ao.iloc[-2] > ao.iloc[-3] and
        candles.iloc[-1]['close'] < candles.iloc[-1]['open'] and
        candles.iloc[-2]['close'] < candles.iloc[-2]['open'] and
        cci.iloc[-2] > 100 and cci.iloc[-1] > cci.iloc[-2] and
        fractal == "bullish"):
        return "BUY", ao, cci

    # SELL
    if (ao.iloc[-1] < 0 and ao.iloc[-1] < ao.iloc[-2] < ao.iloc[-3] and
        candles.iloc[-1]['close'] > candles.iloc[-1]['open'] and
        candles.iloc[-2]['close'] > candles.iloc[-2]['open'] and
        cci.iloc[-2] < -100 and cci.iloc[-1] < cci.iloc[-2] and
        fractal == "bearish"):
        return "SELL", ao, cci

    return None, None, None

# === BOT LOOP ===
def run():
    global last_signal_time, losing_streak

    while True:
        try:
            if not valid_session():
                time.sleep(60)
                continue

            if losing_streak >= 3:
                bot.send_message(TELEGRAM_BOT_TOKEN,TELEGRAM_BOT_TOKENtext="🛑 Bot paused (losing streak)")
                time.sleep(600)
                continue

            for otc_name, symbol in OTC_PAIRS.items():
                df = get_data(symbol)
                signal, ao, cci = check_signal(df)

                if signal and (time.time() - last_signal_time > COOLDOWN):
                    last_signal_time = time.time()

                    strength = signal_strength(ao, cci)

                    message = f"""
📊 {signal} SIGNAL

💱 Pair: {otc_name}
⏱ Timeframe: M1
⏳ Expiry: 1–2 min

🔥 Strength: {strength}

📊 Setup:
• AO Trend confirmed
• Pullback valid
• Fractal + CCI trigger

📡 Data: Proxy (live market)
⚠️ OTC may differ

🕒 Entry: Next candle open

📊 Stats:
Wins: {wins} | Losses: {losses}
"""

                    bot.send_message(TELEGRAM_BOT_TOKEN =TELEGRAM_BOT_TOKEN, text=message)

            time.sleep(60)

        except Exception as e:
            print("Error:", e)
            time.sleep(60)

if __name__ == "__main__":
    run()
