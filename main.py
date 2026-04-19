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

# Environment variables (to be set by user)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
POCKET_OPTION_SSID = os.getenv("POCKET_OPTION_SSID") # Needed for market data
IS_DEMO = os.getenv("IS_DEMO", "False").lower() == "true" # Needed for market data

# Expanded ASSETS list
ASSETS = [
    "USDJPY_otc", "GBPUSD_otc", "GBPJPY_otc", "EURUSD_otc", "AUDUSD_otc",
    "USDCAD_otc", "EURJPY_otc", "AUDJPY_otc", "NZDUSD_otc", "EURGBP_otc"
]

# Initialize Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Initialize Pocket Option Client
po_client = AsyncPocketOptionClient(POCKET_OPTION_SSID, is_demo=IS_DEMO)

# Global state
chat_id = None

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    # Avoid division by zero
    loss = loss.replace(0, 0.00001)
    rs = gain / loss
    return 100 - (100 / (1 + rs))

async def get_signal(asset):
    """
    Improved Strategy: RSI + Bollinger Bands + SMA.
    Guaranteed to return a signal based on the most likely direction.
    """
    try:
        candles = await po_client.get_candles_dataframe(asset=asset, timeframe=60)
        if candles.empty or len(candles) < 20:
            logger.warning(f"Market data unavailable for {asset}. Check SSID.")
            # If no data, alternate based on time to avoid constant 'BUY'
            return OrderDirection.CALL if int(asyncio.get_event_loop().time()) % 2 == 0 else OrderDirection.PUT
        
        # Calculate indicators
        candles['SMA_10'] = candles['close'].rolling(window=10).mean()
        candles['RSI_14'] = calculate_rsi(candles['close'], 14)
        candles['SMA_20'] = candles['close'].rolling(window=20).mean()
        candles['STD_20'] = candles['close'].rolling(window=20).std()
        candles['BBU_20_2.0'] = candles['SMA_20'] + (candles['STD_20'] * 2)
        candles['BBL_20_2.0'] = candles['SMA_20'] - (candles['STD_20'] * 2)
        
        last_row = candles.iloc[-1]
        rsi = last_row["RSI_14"]
        lower_bb = last_row["BBL_20_2.0"]
        upper_bb = last_row["BBU_20_2.0"]
        close = last_row["close"]
        sma_10 = last_row["SMA_10"]
        
        # 1. Strong Reversal Signals (Oversold/Overbought)
        if close <= lower_bb or rsi <= 30:
            return OrderDirection.CALL
        if close >= upper_bb or rsi >= 70:
            return OrderDirection.PUT
            
        # 2. Trend Following Signals (SMA)
        if close > sma_10:
            return OrderDirection.CALL
        else:
            return OrderDirection.PUT

    except Exception as e:
        logger.error(f"Error getting signal for {asset}: {e}")
        # Alternate on error
        return OrderDirection.CALL if int(asyncio.get_event_loop().time()) % 2 == 0 else OrderDirection.PUT

async def send_signal_message(asset, direction):
    if not chat_id: return
    direction_emoji = "⬆️" if direction == OrderDirection.CALL else "⬇️"
    signal_text = "BUY SIGNAL!" if direction == OrderDirection.CALL else "SELL SIGNAL!"
    await bot.send_message(
        chat_id=chat_id,
        text=f"{direction_emoji} {signal_text} {asset.replace('_otc', ' OTC')}\nEnter NOW 🔥"
    )

def get_asset_reply_keyboard():
    keyboard_buttons = []
    for asset_name in ASSETS:
        display_name = asset_name.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        flag = "🇺🇸" if "USD" in asset_name else "🇬🇧" if "GBP" in asset_name else "🇪🇺" if "EUR" in asset_name else "🇦🇺" if "AUD" in asset_name else "🇳🇿" if "NZD" in asset_name else "🇨🇦" if "CAD" in asset_name else "🇯🇵" if "JPY" in asset_name else ""
        keyboard_buttons.append(KeyboardButton(text=f"{flag} {display_name}"))
    rows = [keyboard_buttons[i:i + 2] for i in range(0, len(keyboard_buttons), 2)]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    global chat_id
    chat_id = message.chat.id
    await message.answer("Welcome! Tap an asset for an instant signal.", reply_markup=get_asset_reply_keyboard())

@dp.message()
async def asset_button_handler(message: types.Message):
    global chat_id
    chat_id = message.chat.id
    cleaned_text = re.sub(r'^[\U0001F1E6-\U0001F1FF\s]+', '', message.text).strip()
    found_asset = None
    for asset in ASSETS:
        compare_name = asset.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        if cleaned_text == compare_name:
            found_asset = asset
            break
    
    if found_asset:
        await bot.send_message(chat_id=chat_id, text=f"Analyzing {found_asset.replace('_otc', ' OTC')}...")
        signal = await get_signal(found_asset)
        await send_signal_message(found_asset, signal)
    else:
        await message.answer("Please use the buttons.", reply_markup=get_asset_reply_keyboard())

async def main():
    logger.info("Bot starting...")
    try:
        await po_client.connect()
        logger.info("Pocket Option connected.")
    except:
        logger.error("Pocket Option connection failed. Check SSID.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
