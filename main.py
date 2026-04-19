import os
import asyncio
import logging
import re
import pandas as pd
import pandas_ta as ta
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

# Initialize Pocket Option Client (re-introduced for market data)
po_client = AsyncPocketOptionClient(POCKET_OPTION_SSID, is_demo=IS_DEMO)

# Global state
chat_id = None

async def get_signal(asset):
    """
    Strategy: RSI + Bollinger Bands with a fallback to SMA trend.
    This function is guaranteed to return a signal (CALL or PUT).
    - CALL: Price below lower BB and RSI < 30, OR (fallback) Price above SMA_10.
    - PUT: Price above upper BB and RSI > 70, OR (fallback) Price below SMA_10.
    """
    try:
        candles = await po_client.get_candles_dataframe(asset=asset, timeframe=60)
        if candles.empty or len(candles) < 20: # Need enough data for BB and SMA
            logger.warning(f"Not enough candle data for {asset} to generate a signal. Using default CALL.")
            return OrderDirection.CALL # Default to CALL if not enough data
        
        # Calculate indicators
        candles.ta.rsi(length=14, append=True)
        candles.ta.bbands(length=20, std=2, append=True)
        candles.ta.sma(length=10, append=True) # Add SMA for fallback
        
        last_row = candles.iloc[-1]
        rsi = last_row["RSI_14"]
        lower_bb = last_row["BBL_20_2.0"]
        upper_bb = last_row["BBU_20_2.0"]
        close = last_row["close"]
        sma_10 = last_row["SMA_10"]
        
        # Primary conditions
        if close < lower_bb and rsi < 30:
            return OrderDirection.CALL
        elif close > upper_bb and rsi > 70:
            return OrderDirection.PUT
        
        # Fallback if primary conditions are not met
        if close > sma_10:
            return OrderDirection.CALL
        elif close < sma_10:
            return OrderDirection.PUT
        
        # If all else fails (e.g., price is exactly on SMA), default to CALL
        return OrderDirection.CALL

    except Exception as e:
        logger.error(f"Error getting signal for {asset}: {e}. Using default CALL.")
        return OrderDirection.CALL # Default to CALL on error

async def send_signal_message(asset, direction):
    if not chat_id:
        logger.warning("Chat ID not set, cannot send signal message.")
        return

    direction_emoji = "⬆️" if direction == OrderDirection.CALL else "⬇️"
    signal_text = "BUY SIGNAL!" if direction == OrderDirection.CALL else "SELL SIGNAL!"
    
    await bot.send_message(
        chat_id=chat_id,
        text=f"{direction_emoji} {signal_text} {asset.replace('_otc', ' OTC')}\nEnter NOW 🔥"
    )

# Create a persistent ReplyKeyboardMarkup with asset buttons in a square grid
def get_asset_reply_keyboard():
    keyboard_buttons = []
    for asset_name in ASSETS:
        # Format asset name for button (e.g., USD/JPY OTC)
        display_asset_name = asset_name.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        # Add flag emoji based on the first currency in the pair
        flag_emoji = ""
        if "USD" in asset_name:
            flag_emoji = "🇺🇸"
        elif "GBP" in asset_name:
            flag_emoji = "🇬🇧"
        elif "EUR" in asset_name:
            flag_emoji = "🇪🇺"
        elif "AUD" in asset_name:
            flag_emoji = "🇦🇺"
        elif "NZD" in asset_name:
            flag_emoji = "🇳🇿"
        elif "CAD" in asset_name:
            flag_emoji = "🇨🇦"
        elif "JPY" in asset_name:
            flag_emoji = "🇯🇵"
        
        keyboard_buttons.append(KeyboardButton(text=f"{flag_emoji} {display_asset_name}"))
    
    # Arrange buttons in rows of 2 for a square grid look
    rows = [keyboard_buttons[i:i + 2] for i in range(0, len(keyboard_buttons), 2)]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    global chat_id
    chat_id = message.chat.id
    await message.answer(
        "Welcome to Pocket Option Signal Bot!\nTap an asset below to get an instant signal.",
        reply_markup=get_asset_reply_keyboard()
    )

@dp.message(Command("run"))
async def run_handler(message: types.Message):
    global chat_id
    chat_id = message.chat.id
    await message.answer("Bot is ready! Tap an asset below to get a signal.", reply_markup=get_asset_reply_keyboard())

@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    await message.answer("Bot stopped. To get signals again, use /run or /start.", reply_markup=ReplyKeyboardRemove())

@dp.message()
async def asset_button_handler(message: types.Message):
    global chat_id
    chat_id = message.chat.id

    # Clean the message text to match asset names (remove flag emojis and extra spaces)
    # Regex to remove any sequence of flag emojis at the start, followed by a space
    cleaned_message_text = re.sub(r'^[\U0001F1E6-\U0001F1FF\s]+', '', message.text).strip()

    found_asset = None
    for asset_name in ASSETS:
        # Prepare the asset_name for comparison, matching the cleaned button text format
        # Ensure this matches how the button text is generated, without flags for comparison
        compare_asset_name = asset_name.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        if cleaned_message_text == compare_asset_name:
            found_asset = asset_name
            break
    
    if found_asset:
        await bot.send_message(chat_id=chat_id, text=f"Getting signal for {found_asset.replace('_otc', ' OTC')}...")
        signal = await get_signal(found_asset)
        # The get_signal function is now guaranteed to return a signal
        await send_signal_message(found_asset, signal)
    else:
        # If it's not an asset button, just acknowledge or ignore
        await message.answer("Please use the asset buttons to get signals.", reply_markup=get_asset_reply_keyboard())

async def main():
    logger.info("Starting bot...")
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set!")
        return
    if not POCKET_OPTION_SSID:
        logger.error("POCKET_OPTION_SSID is not set!")
        # We'll continue, but signals might fail
    
    try:
        logger.info("Connecting to Pocket Option...")
        await po_client.connect()
        logger.info("Connected to Pocket Option successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to Pocket Option: {e}")

    logger.info("Starting Telegram polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error during polling: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
