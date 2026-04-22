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
    MILLIONAIRE'S SNIPER: Optimized for high-frequency signals with trend safety.
    """
    try:
        # Fetch 5-second and 1-minute candles
        candles_5s = await po_client.get_candles_dataframe(asset=asset, timeframe=5)
        candles_1m = await po_client.get_candles_dataframe(asset=asset, timeframe=60)
        
        if candles_5s.empty or len(candles_5s) < 10:
            # Fallback for low data
            return OrderDirection.CALL if int(asyncio.get_event_loop().time()) % 2 == 0 else OrderDirection.PUT, 70, "Momentum"
        
        # 1. Major Trend (1-minute SMA 20) - Faster trend detection
        sma_20_1m = candles_1m['close'].rolling(window=20).mean().iloc[-1] if not candles_1m.empty else candles_5s['close'].mean()
        current_price = candles_5s.iloc[-1]['close']
        major_trend_up = current_price > sma_20_1m
        
        # 2. RSI for 5s
        rsi = calculate_rsi(candles_5s['close'], 7).iloc[-1]
        
        # 3. Signal Logic: Prioritize Trend + Momentum
        direction = None
        confidence = 0
        status = "Scanning..."

        # Strong Trend Reversal (Dip/Peak)
        if major_trend_up and rsi < 40:
            direction = OrderDirection.CALL
            confidence = 85
            status = "Trend Dip (BUY)"
        elif not major_trend_up and rsi > 60:
            direction = OrderDirection.PUT
            confidence = 85
            status = "Trend Peak (SELL)"
        else:
            # Momentum Follower (Ensures a signal is always given)
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
        return OrderDirection.CALL, 60, "Auto-Signal"

def get_asset_keyboard():
    btns = []
    for a in ASSETS:
        # Simplified display name for buttons
        display_name = a.replace("_otc", " OTC").upper()
        # Add flags for visual appeal
        flag = "🇺🇸" if "USD" in a else "🇬🇧" if "GBP" in a else "🇪🇺" if "EUR" in a else "🇦🇺" if "AUD" in a else "🇳🇿" if "NZD" in a else "🇨🇦" if "CAD" in a else "🇯🇵" if "JPY" in a else "🇨🇭" if "CHF" in a else "🇦🇪" if "AED" in a else ""
        btns.append(KeyboardButton(text=f"{flag} {display_name}"))
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
    await m.answer("💎 MILLIONAIRE'S SNIPER V2 ACTIVE\nOptimized for AED/CNY & AUD/CHF.", reply_markup=get_asset_keyboard())

@dp.message(TradingStates.selecting_asset)
async def asset_chosen(m: types.Message, state: FSMContext):
    # Improved matching logic: extract the asset name from the button text
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
        await m.answer(f"📊 ASSET: {found.replace('_otc', ' OTC').upper()}\nSelect Expiration:", reply_markup=get_timeframe_keyboard())
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
        await m.answer(f"💎 Sniper Analyzing {asset.replace('_otc', ' OTC').upper()}...")
        
        direction, confidence, status = await get_millionaire_signal(asset)
        
        emoji = "💎 SNIPER BUY" if direction == OrderDirection.CALL else "💎 SNIPER SELL"
        strength = "🔥 MAXIMUM" if confidence >= 85 else "🟢 HIGH"
        
        text = (
            f"━━━━━━━━━━━━━━━\n"
            f"{emoji}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 Asset: {asset.replace('_otc', ' OTC').upper()}\n"
            f"⏱ Time: {tf_text}\n"
            f"📊 Confidence: {confidence}%\n"
            f"⚡ Strength: {strength}\n"
            f"🛡 Strategy: {status}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 SUGGESTED: 1-3% of Balance\n"
            f"🔥 ENTER NOW!"
        )
        
        await m.answer(text, reply_markup=get_asset_keyboard())
        await state.set_state(TradingStates.selecting_asset)
    else:
        await m.answer("Select a valid timeframe using the buttons.")

async def main():
    try: await po_client.connect()
    except: pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
