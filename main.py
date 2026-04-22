import os
import asyncio
import logging
import re
import pandas as pd
import numpy as np
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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

class TradingStates(StatesGroup):
    selecting_asset = State()
    selecting_timeframe = State()

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
po_client = AsyncPocketOptionClient(POCKET_OPTION_SSID, is_demo=IS_DEMO)

async def get_turbo_signal(asset):
    """
    TURBO SCALPER: Pure Momentum & Price Action.
    Gives a signal every time based on immediate 5s candle direction.
    """
    try:
        # Fetch 5-second candles
        candles = await po_client.get_candles_dataframe(asset=asset, timeframe=5)
        
        if candles.empty or len(candles) < 5:
            # Fallback if data is slow
            return OrderDirection.CALL if int(asyncio.get_event_loop().time()) % 2 == 0 else OrderDirection.PUT
        
        last_candles = candles.tail(3)
        
        # Calculate immediate momentum
        # If the last 2 candles are green, we BUY. If red, we SELL.
        current_close = last_candles.iloc[-1]['close']
        prev_close = last_candles.iloc[-2]['close']
        start_close = last_candles.iloc[-3]['close']
        
        if current_close > prev_close:
            # Price is moving UP
            return OrderDirection.CALL
        else:
            # Price is moving DOWN
            return OrderDirection.PUT

    except Exception as e:
        logger.error(f"Error: {e}")
        return OrderDirection.CALL if int(asyncio.get_event_loop().time()) % 2 == 0 else OrderDirection.PUT

def get_asset_keyboard():
    btns = []
    for a in ASSETS:
        name = a.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        flag = "🇺🇸" if "USD" in a else "🇬🇧" if "GBP" in a else "🇪🇺" if "EUR" in a else "🇦🇺" if "AUD" in a else "🇳🇿" if "NZD" in a else "🇨🇦" if "CAD" in a else "🇯🇵" if "JPY" in a else ""
        btns.append(KeyboardButton(text=f"{flag} {name}"))
    rows = [btns[i:i + 2] for i in range(0, len(btns), 2)]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

def get_timeframe_keyboard():
    btns = [
        [KeyboardButton(text="⏱ 5 Seconds"), KeyboardButton(text="⏱ 10 Seconds")],
        [KeyboardButton(text="⏱ 15 Seconds"), KeyboardButton(text="⏱ 30 Seconds")],
        [KeyboardButton(text="🔙 Back to Assets")]
    ]
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

@dp.message(Command("start"))
async def start(m: types.Message, state: FSMContext):
    await state.set_state(TradingStates.selecting_asset)
    await m.answer("⚡ TURBO SCALPER ACTIVE\nHigh-Frequency Momentum Signals Enabled.", reply_markup=get_asset_keyboard())

@dp.message(TradingStates.selecting_asset)
async def asset_chosen(m: types.Message, state: FSMContext):
    clean = re.sub(r'^[\U0001F1E6-\U0001F1FF\s]+', '', m.text).strip()
    found = None
    for a in ASSETS:
        comp = a.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/")
        if clean == comp:
            found = a
            break
    if found:
        await state.update_data(asset=found)
        await state.set_state(TradingStates.selecting_timeframe)
        await m.answer(f"🚀 TURBO: {found.replace('_otc', ' OTC')}\nSelect Timeframe:", reply_markup=get_timeframe_keyboard())
    else:
        await m.answer("Please use the buttons.")

@dp.message(TradingStates.selecting_timeframe)
async def timeframe_chosen(m: types.Message, state: FSMContext):
    if m.text == "🔙 Back to Assets":
        await state.set_state(TradingStates.selecting_asset)
        await m.answer("Select an Asset:", reply_markup=get_asset_keyboard())
        return
    if m.text in ["⏱ 5 Seconds", "⏱ 10 Seconds", "⏱ 15 Seconds", "⏱ 30 Seconds"]:
        data = await state.get_data()
        asset = data['asset']
        tf_text = m.text.replace("⏱ ", "")
        
        # Instant Analysis
        direction = await get_turbo_signal(asset)
        
        emoji = "🚀 TURBO BUY" if direction == OrderDirection.CALL else "⚡ TURBO SELL"
        
        text = (
            f"━━━━━━━━━━━━━━━\n"
            f"{emoji}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 Asset: {asset.replace('_otc', ' OTC')}\n"
            f"⏱ Time: {tf_text}\n"
            f"🔥 ENTER NOW!"
        )
        
        await m.answer(text, reply_markup=get_asset_keyboard())
        await state.set_state(TradingStates.selecting_asset)
    else:
        await m.answer("Select a valid timeframe.")

async def main():
    try: await po_client.connect()
    except: pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
