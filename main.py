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
    "USDCAD_otc", "EURJPY_otc", "AUDJPY_otc", "NZDUSD_otc", "EURGBP_otc",
    "AUDCAD_otc", "AUDCHF_otc", "AEDCNY_otc"
]

class TradingStates(StatesGroup):
    selecting_asset = State()
    selecting_timeframe = State()

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
po_client = AsyncPocketOptionClient(POCKET_OPTION_SSID, is_demo=IS_DEMO)

def calculate_rsi(series, period=7):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    loss = loss.replace(0, 0.00001)
    rs = gain / loss
    return 100 - (100 / (1 + rs))

async def get_millionaire_signal(asset):
    """
    MILLIONAIRE'S SNIPER: With SSID Expiration Detection.
    """
    try:
        # Check connection first
        if not po_client.is_connected:
            try:
                await po_client.connect()
                await asyncio.sleep(1) # Give it a second to stabilize
            except:
                return None, 0, "SSID EXPIRED"

        # Fetch candles
        candles_5s = await po_client.get_candles_dataframe(asset=asset, timeframe=5)
        
        if candles_5s.empty or len(candles_5s) < 5:
            # Try one more time to connect
            await po_client.connect()
            await asyncio.sleep(1)
            candles_5s = await po_client.get_candles_dataframe(asset=asset, timeframe=5)
            if candles_5s.empty:
                return None, 0, "SSID EXPIRED"
        
        candles_1m = await po_client.get_candles_dataframe(asset=asset, timeframe=60)
        
        # 1. Major Trend
        sma_20_1m = candles_1m['close'].rolling(window=20).mean().iloc[-1] if not candles_1m.empty else candles_5s['close'].mean()
        current_price = candles_5s.iloc[-1]['close']
        major_trend_up = current_price > sma_20_1m
        
        # 2. RSI
        rsi = calculate_rsi(candles_5s['close'], 7).iloc[-1]
        
        # 3. Signal Logic
        direction = None
        confidence = 0
        status = "Scanning..."

        if major_trend_up and rsi < 40:
            direction = OrderDirection.CALL
            confidence = 85
            status = "Trend Dip (BUY)"
        elif not major_trend_up and rsi > 60:
            direction = OrderDirection.PUT
            confidence = 85
            status = "Trend Peak (SELL)"
        else:
            last_diff = candles_5s['close'].diff().tail(3).sum()
            if last_diff > 0:
                direction = OrderDirection.CALL
                confidence = 75
                status = "Bullish Momentum"
            else:
                direction = OrderDirection.PUT
                confidence = 75
                status = "Bearish Momentum"

        return direction, confidence, status

    except Exception as e:
        logger.error(f"Error: {e}")
        return None, 0, "SSID EXPIRED"

def get_asset_keyboard():
    btns = []
    for a in ASSETS:
        display_name = a.replace("_otc", " OTC").upper()
        
        if "USDJPY" in a: flag_pair = "🇺🇸/🇯🇵"
        elif "GBPUSD" in a: flag_pair = "🇬🇧/🇺🇸"
        elif "GBPJPY" in a: flag_pair = "🇬🇧/🇯🇵"
        elif "EURUSD" in a: flag_pair = "🇪🇺/🇺🇸"
        elif "AUDUSD" in a: flag_pair = "🇦🇺/🇺🇸"
        elif "USDCAD" in a: flag_pair = "🇺🇸/🇨🇦"
        elif "EURJPY" in a: flag_pair = "🇪🇺/🇯🇵"
        elif "AUDJPY" in a: flag_pair = "🇦🇺/🇯🇵"
        elif "NZDUSD" in a: flag_pair = "🇳🇿/🇺🇸"
        elif "EURGBP" in a: flag_pair = "🇪🇺/🇬🇧"
        elif "AUDCAD" in a: flag_pair = "🇦🇺/🇨🇦"
        elif "AUDCHF" in a: flag_pair = "🇦🇺/🇨🇭"
        elif "AEDCNY" in a: flag_pair = "🇦🇪/🇨🇳"
        else: flag_pair = "🏳️"

        btns.append(KeyboardButton(text=f"{flag_pair} {display_name}"))
    
    # Create a square grid (2 buttons per row)
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
    await m.answer("💎 MILLIONAIRE'S SNIPER V2 ACTIVE\nSSID Status: Monitoring...", reply_markup=get_asset_keyboard())

@dp.message(TradingStates.selecting_asset)
async def asset_chosen(m: types.Message, state: FSMContext):
    text = m.text.upper()
    found = None
    for a in ASSETS:
        asset_key = a.replace("_otc", "").upper()
        if asset_key in text:
            found = a
            break
    
    if found:
        await state.update_data(asset=found)
        await state.set_state(TradingStates.selecting_timeframe)
        display_name = found.replace("_otc", " OTC").upper()
        await m.answer(f"📊 ASSET: {display_name}\nSelect Expiration:", reply_markup=get_timeframe_keyboard())
    else:
        await m.answer("Please use the buttons provided below.", reply_markup=get_asset_keyboard())

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
        
        direction, confidence, status = await get_millionaire_signal(asset)
        
        if status == "SSID EXPIRED":
            await m.answer("❌ ERROR: SSID EXPIRED\n\nPlease get a fresh SSID from your browser and update it in Railway to continue receiving real signals.", reply_markup=get_asset_keyboard())
            await state.set_state(TradingStates.selecting_asset)
            return

        if direction == OrderDirection.CALL:
            signal_text = f"⬆️ BUY SIGNAL! 🚀\n⏱ Time: {tf_text}\nEnter NOW 🔥"
        else:
            signal_text = f"⬇️ SELL SIGNAL! 🚨\n⏱ Time: {tf_text}\nEnter NOW 🔥"
        
        await m.answer(signal_text, reply_markup=get_asset_keyboard())
        await state.set_state(TradingStates.selecting_asset)
    else:
        await m.answer("Select a valid timeframe using the buttons.")

async def main():
    try: await po_client.connect()
    except: pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
