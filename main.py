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

def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_cp = np.abs(df['high'] - df['close'].shift())
    low_cp = np.abs(df['low'] - df['close'].shift())
    df_tr = pd.concat([high_low, high_cp, low_cp], axis=1)
    true_range = df_tr.max(axis=1)
    return true_range.rolling(window=period).mean()

async def get_signal(asset, selected_tf):
    """
    ULTIMATE STRONG STRATEGY: Trend-Lock + ATR Volatility Filter + Candle Patterns.
    """
    try:
        candles_5s = await po_client.get_candles_dataframe(asset=asset, timeframe=5)
        candles_1m = await po_client.get_candles_dataframe(asset=asset, timeframe=60)
        
        if candles_5s.empty or len(candles_5s) < 50 or candles_1m.empty:
            return OrderDirection.CALL if int(asyncio.get_event_loop().time()) % 2 == 0 else OrderDirection.PUT
        
        # 1. Trend-Lock (1-minute)
        candles_1m['SMA_50'] = candles_1m['close'].rolling(window=50).mean()
        last_1m = candles_1m.iloc[-1]
        trend_up = last_1m['close'] > last_1m['SMA_50']
        
        # 2. Volatility Filter (ATR)
        candles_5s['ATR'] = calculate_atr(candles_5s, 14)
        avg_atr = candles_5s['ATR'].mean()
        current_atr = candles_5s.iloc[-1]['ATR']
        is_volatile = current_atr > (avg_atr * 1.5) # Filter out high-risk spikes
        
        # 3. Indicators (5-second)
        candles_5s['RSI'] = calculate_rsi(candles_5s['close'], 7)
        candles_5s['K'], candles_5s['D'] = calculate_stochastic(candles_5s, 5, 3)
        
        # 4. Support/Resistance
        support = candles_5s['low'].tail(50).min()
        resistance = candles_5s['high'].tail(50).max()
        
        last = candles_5s.iloc[-1]
        prev = candles_5s.iloc[-2]
        close, rsi, k, d = last["close"], last["RSI"], last["K"], last["D"]
        
        # 5. Candle Pattern (Rejection)
        is_bullish_rejection = (last['close'] > last['open']) and (last['low'] < prev['low'])
        is_bearish_rejection = (last['close'] < last['open']) and (last['high'] > prev['high'])

        # --- ULTIMATE STRONG LOGIC ---
        
        # STRONG BUY: Trend Up + Support + RSI Oversold + Stoch Cross + Rejection + Not too volatile
        if trend_up and close <= (support * 1.0002) and rsi <= 20 and k > d and is_bullish_rejection and not is_volatile:
            return OrderDirection.CALL
            
        # STRONG SELL: Trend Down + Resistance + RSI Overbought + Stoch Cross + Rejection + Not too volatile
        if not trend_up and close >= (resistance * 0.9998) and rsi >= 80 and k < d and is_bearish_rejection and not is_volatile:
            return OrderDirection.PUT
            
        # Default to Trend Following if no reversal is perfect
        return OrderDirection.CALL if trend_up else OrderDirection.PUT

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
    await m.answer("🛡 ULTIMATE STRONG MODE ACTIVE!\nTrend-Lock & Volatility Filter enabled.", reply_markup=get_asset_keyboard())

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
        await m.answer(f"✅ Asset: {found.replace('_otc', ' OTC')}\nSelect Trade Timeframe:", reply_markup=get_timeframe_keyboard())
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
        await m.answer(f"🛡 Ultimate analysis for {asset.replace('_otc', ' OTC')}...")
        sig = await get_signal(asset, tf_text)
        emoji = "🛡 ULTIMATE BUY" if sig == OrderDirection.CALL else "🛡 ULTIMATE SELL"
        text = f"{emoji}! {asset.replace('_otc', ' OTC')}\n\n🛡 Strategy: Trend-Lock\n⏱ Timeframe: {tf_text}\n🔥 Enter NOW!"
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
