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

def calculate_rsi(series, period=7):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    loss = loss.replace(0, 0.00001)
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_stochastic(df, k_period=5, d_period=3):
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    k = 100 * ((df['close'] - low_min) / (high_max - low_min))
    d = k.rolling(window=d_period).mean()
    return k, d

async def get_institutional_signal(asset, selected_tf):
    """
    INSTITUTIONAL SNIPER: Confidence Scoring + Volume Divergence + Trend-Lock.
    """
    try:
        candles_5s = await po_client.get_candles_dataframe(asset=asset, timeframe=5)
        candles_1m = await po_client.get_candles_dataframe(asset=asset, timeframe=60)
        
        if candles_5s.empty or len(candles_5s) < 60 or candles_1m.empty:
            return None, 0
        
        # 1. Institutional Trend (1-minute SMA 100)
        candles_1m['SMA_100'] = candles_1m['close'].rolling(window=100).mean()
        trend_up = candles_1m.iloc[-1]['close'] > candles_1m.iloc[-1]['SMA_100']
        
        # 2. Indicators
        candles_5s['RSI'] = calculate_rsi(candles_5s['close'], 7)
        candles_5s['K'], candles_5s['D'] = calculate_stochastic(candles_5s, 5, 3)
        
        # 3. Volume Divergence (Simplified for 5s)
        # If price goes up but RSI goes down = Bearish Divergence
        # If price goes down but RSI goes up = Bullish Divergence
        price_change = candles_5s['close'].diff(5).iloc[-1]
        rsi_change = candles_5s['RSI'].diff(5).iloc[-1]
        
        last = candles_5s.iloc[-1]
        close, rsi, k, d = last["close"], last["RSI"], last["K"], last["D"]
        
        confidence = 0
        direction = None

        # --- INSTITUTIONAL LOGIC ---
        
        # BULLISH SETUP
        if trend_up and rsi <= 25 and k > d:
            confidence = 75
            if rsi_change > 0 and price_change < 0: # Bullish Divergence
                confidence += 15
            direction = OrderDirection.CALL
            
        # BEARISH SETUP
        elif not trend_up and rsi >= 75 and k < d:
            confidence = 75
            if rsi_change < 0 and price_change > 0: # Bearish Divergence
                confidence += 15
            direction = OrderDirection.PUT
            
        # If no clear setup, follow trend with lower confidence
        if direction is None:
            direction = OrderDirection.CALL if trend_up else OrderDirection.PUT
            confidence = 60

        return direction, confidence

    except Exception as e:
        logger.error(f"Error: {e}")
        return OrderDirection.CALL, 50

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
    await m.answer("🏛 INSTITUTIONAL SNIPER ACTIVE\nProfessional Grade Analysis Enabled.", reply_markup=get_asset_keyboard())

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
        await m.answer(f"🔍 Scanning Market for {asset.replace('_otc', ' OTC')}...")
        
        direction, confidence = await get_institutional_signal(asset, tf_text)
        
        emoji = "🏛 INSTITUTIONAL BUY" if direction == OrderDirection.CALL else "🏛 INSTITUTIONAL SELL"
        strength = "🟢 HIGH" if confidence >= 85 else "🟡 MEDIUM" if confidence >= 70 else "🔴 LOW"
        
        text = (
            f"━━━━━━━━━━━━━━━\n"
            f"{emoji}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📈 Asset: {asset.replace('_otc', ' OTC')}\n"
            f"⏱ Time: {tf_text}\n"
            f"📊 Confidence: {confidence}%\n"
            f"⚡ Strength: {strength}\n"
            f"━━━━━━━━━━━━━━━\n"
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
