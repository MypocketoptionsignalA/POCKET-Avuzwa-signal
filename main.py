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
    MILLIONAIRE'S SNIPER: Advanced Trend-Following + Volatility Protection.
    Focuses on high-probability entries only.
    """
    try:
        # Fetch 5-second and 1-minute candles for multi-timeframe analysis
        candles_5s = await po_client.get_candles_dataframe(asset=asset, timeframe=5)
        candles_1m = await po_client.get_candles_dataframe(asset=asset, timeframe=60)
        
        if candles_5s.empty or len(candles_5s) < 50 or candles_1m.empty:
            return None, 0, "Wait for Data"
        
        # 1. Major Trend (1-minute SMA 50)
        sma_50_1m = candles_1m['close'].rolling(window=50).mean().iloc[-1]
        current_price_1m = candles_1m.iloc[-1]['close']
        major_trend_up = current_price_1m > sma_50_1m
        
        # 2. Volatility Check (ATR-like)
        recent_volatility = (candles_5s['high'] - candles_5s['low']).tail(10).mean()
        avg_volatility = (candles_5s['high'] - candles_5s['low']).tail(50).mean()
        
        if recent_volatility > (avg_volatility * 2.5):
            return None, 0, "High Volatility (Danger)"
            
        # 3. Momentum & RSI
        rsi = calculate_rsi(candles_5s['close'], 7).iloc[-1]
        
        # 4. Signal Logic: Only trade WITH the major trend
        direction = None
        confidence = 0
        status = "Scanning..."

        # BULLISH SETUP: Major Trend is UP + 5s RSI is low (Dip in a trend)
        if major_trend_up and rsi < 35:
            direction = OrderDirection.CALL
            confidence = 88
            status = "Trend Dip (BUY)"
            
        # BEARISH SETUP: Major Trend is DOWN + 5s RSI is high (Peak in a trend)
        elif not major_trend_up and rsi > 65:
            direction = OrderDirection.PUT
            confidence = 88
            status = "Trend Peak (SELL)"
            
        # If no perfect setup, check for strong immediate momentum
        if direction is None:
            last_3 = candles_5s['close'].tail(3).diff().sum()
            if major_trend_up and last_3 > 0:
                direction = OrderDirection.CALL
                confidence = 75
                status = "Trend Following"
            elif not major_trend_up and last_3 < 0:
                direction = OrderDirection.PUT
                confidence = 75
                status = "Trend Following"
            else:
                return None, 0, "No Clear Setup"

        return direction, confidence, status

    except Exception as e:
        logger.error(f"Error: {e}")
        return None, 0, "Error"

def get_asset_keyboard():
    btns = []
    for a in ASSETS:
        name = a.replace("_otc", " OTC").replace("USD", "USD/").replace("GBP", "GBP/").replace("JPY", "JPY/").replace("AUD", "AUD/").replace("NZD", "NZD/").replace("CAD", "CAD/").replace("CHF", "CHF/").replace("AED", "AED/").replace("CNY", "CNY/")
        flag = "🇺🇸" if "USD" in a else "🇬🇧" if "GBP" in a else "🇪🇺" if "EUR" in a else "🇦🇺" if "AUD" in a else "🇳🇿" if "NZD" in a else "🇨🇦" if "CAD" in a else "🇯🇵" if "JPY" in a else "🇨🇭" if "CHF" in a else "🇦🇪" if "AED" in a else ""
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
    await m.answer("💎 MILLIONAIRE'S SNIPER ACTIVE\nGoal: Safe Growth & High Accuracy.", reply_markup=get_asset_keyboard())

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
        await m.answer(f"📊 ASSET: {found.replace('_otc', ' OTC')}\nSelect Expiration:", reply_markup=get_timeframe_keyboard())
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
        await m.answer(f"💎 Sniper Analyzing {asset.replace('_otc', ' OTC')}...")
        
        direction, confidence, status = await get_millionaire_signal(asset)
        
        if direction is None:
            await m.answer(f"⚠️ NO TRADE: {status}\nMarket is not perfect. Safety first!", reply_markup=get_asset_keyboard())
            await state.set_state(TradingStates.selecting_asset)
            return

        emoji = "💎 SNIPER BUY" if direction == OrderDirection.CALL else "💎 SNIPER SELL"
        strength = "🔥 MAXIMUM" if confidence >= 85 else "🟢 HIGH"
        
        text = (
            f"━━━━━━━━━━━━━━━\n"
            f"{emoji}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 Asset: {asset.replace('_otc', ' OTC')}\n"
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
        await m.answer("Select a valid timeframe.")

async def main():
    try: await po_client.connect()
    except: pass
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
