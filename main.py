import os
import asyncio
import logging
import re
import pandas as pd
import pandas_ta as ta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    Simple strategy: RSI + Bollinger Bands
    - CALL: Price below lower BB and RSI < 30
    - PUT: Price above upper BB and RSI > 70
    """
    try:
        candles = await po_client.get_candles_dataframe(asset=asset, timeframe=60)
        if candles.empty:
            return None
        
        # Calculate indicators
        candles.ta.rsi(length=14, append=True)
        candles.ta.bbands(length=20, std=2, append=True)
        
        last_row = candles.iloc[-1]
        rsi = last_row["RSI_14"]
        lower_bb = last_row["BBL_20_2.0"]
        upper_bb = last_row["BBU_20_2.0"]
        close = last_row["close"]
        
        if close < lower_bb and rsi < 30:
            return OrderDirection.CALL
        elif close > upper_bb and rsi > 70:
            return OrderDirection.PUT
        
        return None
    except Exception as e:
        logger.error(f"Error getting signal for {asset}: {e}")
        return None

async def send_signal_message(asset, direction):
    if not chat_id:
        logger.warning("Chat ID not set, cannot send signal message.")
        return

    direction_emoji = "⬆️" if direction == OrderDirection.CALL else "⬇️"
    signal_text = "BUY SIGNAL!" if direction == OrderDirection.CALL else "SELL SIGNAL!"
    
    await bot.send_message(
        chat_id=chat_id,
        text=f"{direction_emoji} {signal_text} {asset.replace("_otc", " OTC")}\nEnter NOW 🔥"
    )

# Create a persistent InlineKeyboardMarkup with asset buttons
def get_asset_inline_keyboard():
    keyboard_buttons = []
    for asset_name in ASSETS:
        # Format asset name for button (e.g., USD/JPY OTC)
        display_asset_name = asset_name.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        # Use callback_data to trigger signal generation for the specific asset
        keyboard_buttons.append(InlineKeyboardButton(text=f"🇬🇧 {display_asset_name}", callback_data=f"signal_{asset_name}"))
    
    # Arrange buttons in rows (e.g., 1 button per row for a vertical list)
    rows = [[btn] for btn in keyboard_buttons]
    return InlineKeyboardMarkup(inline_keyboard=rows)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    global chat_id
    chat_id = message.chat.id
    await message.answer(
        "Welcome to Pocket Option Signal Bot!\nTap an asset below to get an instant signal.",
        reply_markup=get_asset_inline_keyboard()
    )

@dp.message(Command("run"))
async def run_handler(message: types.Message):
    global chat_id
    chat_id = message.chat.id
    await message.answer("Bot is ready! Tap an asset below to get a signal.", reply_markup=get_asset_inline_keyboard())

@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    await message.answer("Bot stopped. To get signals again, use /run or /start.")

@dp.callback_query(lambda c: c.data and c.data.startswith("signal_"))
async def process_signal_callback(callback_query: types.CallbackQuery):
    global chat_id
    chat_id = callback_query.message.chat.id # Ensure chat_id is set for callbacks
    
    asset = callback_query.data.split("_")[1]
    
    await bot.answer_callback_query(callback_query.id, text=f"Getting signal for {asset.replace('_otc', ' OTC')}...")
    
    signal = await get_signal(asset)
    if signal:
        await send_signal_message(asset, signal)
    else:
        await bot.send_message(chat_id=chat_id, text=f"No clear signal for {asset.replace('_otc', ' OTC')} at the moment.")

async def main():
    await po_client.connect() # Connect to Pocket Option for market data
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
