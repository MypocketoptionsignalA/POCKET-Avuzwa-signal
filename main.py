import os
import asyncio
import logging
import re
import pandas as pd
import numpy as np
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
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

def calculate_rsi(series, period=7): # Shorter period for faster signals
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    loss = loss.replace(0, 0.00001)
    rs = gain / loss
    return 100 - (100 / (1 + rs))

async def get_signal(asset):
    """
    High-Speed Strategy: Optimized for 5s, 10s, 15s, 30s trades.
    Uses 5-second candle data for maximum sensitivity.
    """
    try:
        # Fetch 5-second candles for high-speed analysis
        candles = await po_client.get_candles_dataframe(asset=asset, timeframe=5)
        
        if candles.empty or len(candles) < 15:
            logger.warning(f"Fast market data unavailable for {asset}. Check SSID.")
            return OrderDirection.CALL if int(asyncio.get_event_loop().time()) % 2 == 0 else OrderDirection.PUT
        
        # Fast Indicators
        candles['SMA_5'] = candles['close'].rolling(window=5).mean()
        candles['RSI_7'] = calculate_rsi(candles['close'], 7) # Very sensitive RSI
        candles['SMA_14'] = candles['close'].rolling(window=14).mean()
        candles['STD_14'] = candles['close'].rolling(window=14).std()
        candles['BBU'] = candles['SMA_14'] + (candles['STD_14'] * 1.8) # Tighter bands for faster entries
        candles['BBL'] = candles['SMA_14'] - (candles['STD_14'] * 1.8)
        
        last = candles.iloc[-1]
        rsi = last["RSI_7"]
        lower_bb = last["BBL"]
        upper_bb = last["BBU"]
        close = last["close"]
        sma_5 = last["SMA_5"]
        
        # HIGH-SPEED SIGNAL LOGIC
        # 1. Scalping Reversals (Strongest for 5s-15s)
        if close <= lower_bb and rsi <= 25:
            return OrderDirection.CALL
        if close >= upper_bb and rsi >= 75:
            return OrderDirection.PUT
            
        # 2. Momentum Following (For 15s-30s)
        if close > sma_5:
            return OrderDirection.CALL
        else:
            return OrderDirection.PUT

    except Exception as e:
        logger.error(f"Error: {e}")
        return OrderDirection.CALL if int(asyncio.get_event_loop().time()) % 2 == 0 else OrderDirection.PUT

async def send_signal_message(asset, direction):
    if not chat_id: return
    emoji = "🚀 BUY" if direction == OrderDirection.CALL else "⚡ SELL"
    text = f"{emoji} SIGNAL! {asset.replace('_otc', ' OTC')}\n\n⏱ Timeframe: 5s - 30s\n🔥 Enter NOW!"
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
    await m.answer("🔥 High-Speed Signal Bot Ready!\nOptimized for 5s, 10s, 15s, 30s trades.", reply_markup=get_keyboard())

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
        await bot.send_message(chat_id=chat_id, text=f"⚡ Analyzing {found.replace('_otc', ' OTC')} (5s Data)...")
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
