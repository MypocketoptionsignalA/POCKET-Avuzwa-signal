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
POCKET_OPTION_SSID = os.getenv("POCKET_OPTION_SSID")
IS_DEMO = os.getenv("IS_DEMO", "False").lower() == "true" # Default to real market
TRADE_AMOUNT = float(os.getenv("TRADE_AMOUNT", "1.0"))
TRADE_DURATION = int(os.getenv("TRADE_DURATION", "60"))
ASSETS = os.getenv("ASSETS", "EURUSD_otc,GBPUSD_otc").split(",")

# Initialize Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Initialize Pocket Option Client
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

async def execute_trade(asset, direction):
    if not chat_id:
        logger.warning("Chat ID not set, cannot send trade execution message.")
        return
    try:
        order = await po_client.place_order(
            asset=asset, 
            amount=TRADE_AMOUNT, 
            direction=direction, 
            duration=TRADE_DURATION
        )
        direction_str = "CALL" if direction == OrderDirection.CALL else "PUT"
        await bot.send_message(
            chat_id=chat_id, 
            text=f"✅ Trade placed: {order.order_id}\nAmount: {TRADE_AMOUNT}\nDirection: {direction_str}\nAsset: {asset}"
        )
    except Exception as e:
        await bot.send_message(
            chat_id=chat_id, 
            text=f"❌ Failed to place trade for {asset}: {e}"
        )

async def send_signal_message(asset, direction):
    if not chat_id:
        logger.warning("Chat ID not set, cannot send signal message.")
        return

    direction_emoji = "⬆️" if direction == OrderDirection.CALL else "⬇️"
    signal_text = "BUY SIGNAL!" if direction == OrderDirection.CALL else "SELL SIGNAL!"
    
    # Create inline keyboard for assets
    keyboard_buttons = []
    for asset_name in ASSETS:
        # Format asset name for button (e.g., EUR/USD OTC)
        display_asset_name = asset_name.replace("_otc", " OTC").replace("USD", "USD/")
        keyboard_buttons.append(InlineKeyboardButton(text=f"🇬🇧 {display_asset_name}", callback_data=f"trade_{asset_name}_{direction.value}"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in keyboard_buttons])

    await bot.send_message(
        chat_id=chat_id,
        text=f"{direction_emoji} {signal_text} {asset.replace('_otc', ' OTC')}\nEnter NOW 🔥",
        reply_markup=keyboard
    )

async def trading_loop():
    global is_running
    while is_running:
        for asset in ASSETS:
            signal = await get_signal(asset)
            if signal:
                await send_signal_message(asset, signal)
                await execute_trade(asset, signal) # Auto-trade based on generated signal
            
        await asyncio.sleep(60) # Check every minute for new signals

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Welcome to Pocket Option Signal Bot!\nUse /run to start signal generation and trading, and /stop to stop.")

@dp.message(Command("run"))
async def run_handler(message: types.Message):
    global is_running, chat_id
    if not is_running:
        is_running = True
        chat_id = message.chat.id
        asyncio.create_task(trading_loop())
        await message.answer("Bot started! Generating signals and trading...")
    else:
        await message.answer("Bot is already running.")

@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    global is_running
    is_running = False
    await message.answer("Bot stopped.")

@dp.callback_query(lambda c: c.data and c.data.startswith('trade_'))
async def process_callback_button(callback_query: types.CallbackQuery):
    global chat_id
    chat_id = callback_query.message.chat.id # Ensure chat_id is set for callbacks
    
    action, asset, direction_value = callback_query.data.split('_')
    direction = OrderDirection.CALL if direction_value == str(OrderDirection.CALL.value) else OrderDirection.PUT
    
    await bot.answer_callback_query(callback_query.id, text=f"Executing trade for {asset} {direction.name}...")
    await execute_trade(asset, direction)

async def main():
    await po_client.connect()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()))
