import os
import asyncio
import logging
import re
import pandas as pd
import pandas_ta as ta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from pocketoptionapi_async import AsyncPocketOptionClient, OrderDirection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (to be set by user)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
POCKET_OPTION_SSID = os.getenv("POCKET_OPTION_SSID") # Re-introducing for market data
IS_DEMO = os.getenv("IS_DEMO", "False").lower() == "true" # Re-introducing for market data

# Expanded ASSETS list
ASSETS = [
    "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "GBPJPY_otc", "AUDUSD_otc",
    "USDCAD_otc", "EURJPY_otc", "AUDJPY_otc", "NZDUSD_otc", "EURGBP_otc"
]

# Initialize Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Initialize Pocket Option Client (re-introduced for market data)
po_client = AsyncPocketOptionClient(POCKET_OPTION_SSID, is_demo=IS_DEMO)

# Global state
is_running = False
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
    
    # Create inline keyboard for assets (as in previous version, but now for display)
    keyboard_buttons = []
    for asset_name in ASSETS:
        display_asset_name = asset_name.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        keyboard_buttons.append(InlineKeyboardButton(text=f"🇬🇧 {display_asset_name}", callback_data=f"get_signal_{asset_name}"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in keyboard_buttons])

    await bot.send_message(
        chat_id=chat_id,
        text=f"{direction_emoji} {signal_text} {asset.replace("_otc", " OTC")}\nEnter NOW 🔥",
        reply_markup=keyboard
    )

# Create a persistent ReplyKeyboardMarkup with asset buttons
def get_asset_keyboard():
    keyboard_buttons = []
    for asset_name in ASSETS:
        display_asset_name = asset_name.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        keyboard_buttons.append(KeyboardButton(text=display_asset_name))
    
    # Arrange buttons in rows (e.g., 2 buttons per row)
    rows = [keyboard_buttons[i:i + 2] for i in range(0, len(keyboard_buttons), 2)]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=False)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    global chat_id
    chat_id = message.chat.id
    await message.answer(
        "Welcome to Pocket Option Signal Bot!\nClick an asset button below to get an instant signal.",
        reply_markup=get_asset_keyboard()
    )

@dp.message(Command("run"))
async def run_handler(message: types.Message):
    global is_running, chat_id
    if not is_running:
        is_running = True
        chat_id = message.chat.id
        await message.answer("Bot started! Click an asset button to get a signal.", reply_markup=get_asset_keyboard())
    else:
        await message.answer("Bot is already running.")

@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    global is_running
    is_running = False
    await message.answer("Bot stopped.")

@dp.message()
async def asset_button_handler(message: types.Message):
    global chat_id
    chat_id = message.chat.id

    # Check if the message text matches one of our asset display names
    for asset_name in ASSETS:
        display_asset_name = asset_name.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        if message.text == display_asset_name:
            await message.answer(f"Getting signal for {display_asset_name}...")
            signal = await get_signal(asset_name)
            if signal:
                await send_signal_message(asset_name, signal)
            else:
                await message.answer(f"No clear signal for {display_asset_name} at the moment.")
            return
    
    # If it's not an asset button, just acknowledge or ignore
    if message.text not in [btn.text for row in get_asset_keyboard().keyboard for btn in row]:
        await message.answer("Please use the asset buttons to get signals.", reply_markup=get_asset_keyboard())

async def main():
    await po_client.connect() # Connect to Pocket Option for market data
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()))
