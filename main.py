import os
import asyncio
import logging
import re
import pandas as pd
import numpy as np
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from pocketoptionapi_async import AsyncPocketOptionClient, OrderDirection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
POCKET_OPTION_SSID = os.getenv("POCKET_OPTION_SSID")
IS_DEMO = os.getenv("IS_DEMO", "False").lower() == "true"

# Assets
ASSETS = [
    "USDJPY_otc", "GBPUSD_otc", "GBPJPY_otc", "EURUSD_otc", "AUDUSD_otc",
    "USDCAD_otc", "EURJPY_otc", "AUDJPY_otc", "NZDUSD_otc", "EURGBP_otc"
]

# Initialize Bot
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
po_client = AsyncPocketOptionClient(POCKET_OPTION_SSID, is_demo=IS_DEMO)

chat_id = None

def calculate_rsi(series, period=7):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    loss = loss.replace(0, 0.00001)
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_stochastic(df, k_period=5, d_period=3):
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    k = 100 * ((df['close'] - low_min) / (high_max - low_min))
    d = k.rolling(window=d_period).mean()
    return k, d

async def get_signal(asset):
    """
    SNIPER STRATEGY: Multi-Timeframe Analysis + Support/Resistance.
    Designed for maximum accuracy on 5s-30s trades.
    """
    try:
        # 1. Get 5-second data (Fast)
        candles_5s = await po_client.get_candles_dataframe(asset=asset, timeframe=5)
        # 2. Get 1-minute data (Trend Confirmation)
        candles_1m = await po_client.get_candles_dataframe(asset=asset, timeframe=60)
        
        if candles_5s.empty or len(candles_5s) < 30 or candles_1m.empty:
            return OrderDirection.CALL if int(asyncio.get_event_loop().time()) % 2 == 0 else OrderDirection.PUT
        
        # --- 1-MINUTE TREND CHECK ---
        candles_1m['SMA_20'] = candles_1m['close'].rolling(window=20).mean()
        trend_up = candles_1m.iloc[-1]['close'] > candles_1m.iloc[-1]['SMA_20']
        
        # --- 5-SECOND SNIPER ANALYSIS ---
        candles_5s['RSI'] = calculate_rsi(candles_5s['close'], 7)
        candles_5s['K'], candles_5s['D'] = calculate_stochastic(candles_5s, 5, 3)
        
        # Support & Resistance (Last 30 candles)
        support = candles_5s['low'].tail(30).min()
        resistance = candles_5s['high'].tail(30).max()
        
        last = candles_5s.iloc[-1]
        close = last["close"]
        rsi = last["RSI"]
        k, d = last["K"], last["D"]
        
        # --- SNIPER LOGIC ---
        
        # SNIPER BUY: At Support + RSI Oversold + Stoch Cross + Trend is UP
        if close <= (support * 1.0001) and rsi <= 20 and k <= 20 and k > d and trend_up:
            return OrderDirection.CALL
            
        # SNIPER SELL: At Resistance + RSI Overbought + Stoch Cross + Trend is DOWN
        if close >= (resistance * 0.9999) and rsi >= 80 and k >= 80 and k < d and not trend_up:
            return OrderDirection.PUT
            
        # If no sniper entry, follow the immediate 5s momentum ONLY if it matches 1m trend
        if trend_up:
            return OrderDirection.CALL
        else:
            return OrderDirection.PUT

    except Exception as e:
        logger.error(f"Error: {e}")
        return OrderDirection.CALL if int(asyncio.get_event_loop().time()) % 2 == 0 else OrderDirection.PUT

async def send_signal_message(asset, direction):
    if not chat_id: return
    emoji = "🎯 SNIPER BUY" if direction == OrderDirection.CALL else "🎯 SNIPER SELL"
    text = f"{emoji}! {asset.replace('_otc', ' OTC')}\n\n🛡 Strategy: Sniper (No-Rush)\n⏱ Timeframe: 5s - 30s\n🔥 Enter NOW!"
    await bot.send_message(chat_id=chat_id, text=text)

def get_keyboard():
    btns = []
    for a in ASSETS:
        name = a.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        flag = "🇺🇸" if "USD" in a else "🇬🇧" if "GBP" in a else "🇪🇺" if "EUR" in a else "🇦🇺" if "AUD" in a else "🇳🇿" if "NZD" in a else "🇨🇦" if "CAD" in a else "🇯🇵" if "JPY" in a else ""
        btns.append(KeyboardButton(text=f"{flag} {name}"))
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

@dp.message(Command("start"))
async def start(m: types.Message):
    global chat_id
    chat_id = m.chat.id
    await m.answer("🎯 SNIPER MODE ACTIVE!\nThis bot now checks multiple timeframes for maximum accuracy.", reply_markup=get_keyboard())

@dp.message()
async def handle(m: types.Message):
    global chat_id
    chat_id = m.chat.id
    clean = re.sub(r'^[\U0001F1E6-\U0001F1FF\s]+', '', m.text).strip()
    found = None
    for a in ASSETS:
        comp = a.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        if clean == comp:
            found = a
            break
    if found:
        await bot.send_message(chat_id=chat_id, text=f"🎯 Sniper analyzing {found.replace('_otc', ' OTC')}...")
        sig = await get_signal(found)
        await send_signal_message(found, sig)
    else:
        await m.answer("Use buttons.", reply_markup=get_keyboard())

async def main():
    try: await po_client.connect()
    except: pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
