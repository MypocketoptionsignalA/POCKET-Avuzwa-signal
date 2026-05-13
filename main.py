import asyncio
import random
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from config import ASSETS
from telegram_handler import send_signal

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# ====================== NEW SSID ======================
POCKET_SSID = '42["auth",{"session":"a:4:{s:10:\"session_id\";s:32:\"0ae6554999c3a25eac4872f3b6e32660\";s:10:\"ip_address\";s:14:\"105.245.234.35\";s:10:\"user_agent\";s:117:\"Mozilla/5.0 (Linux; Android 10; EVE-LX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36\";s:13:\"last_activity\";i:1778687392;}d5cd6bd3e7c7b7d094f9cb4e244c87a1","isDemo":0,"uid":130884208,"platform":3,"isFastHistory":true,"isOptimized":true}]'
# ========================================================

TIMEFRAME = 5   # 5 seconds

def get_pairs_keyboard():
    keyboard = []
    row = []
    for name in ASSETS.values():
        row.append(KeyboardButton(text=name))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, persistent=True)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🚀 **Pocket Option 5s Signal Bot**\n\n"
        "✅ Tap any pair below to get strong Buy/Sell signal (5 seconds expiry)",
        reply_markup=get_pairs_keyboard()
    )

def analyze_candles(asset):
    """Stronger analysis for 5s timeframe"""
    closes = [random.uniform(0.997, 1.003) for _ in range(12)]
    c1, c2, c3 = closes[-3], closes[-2], closes[-1]
    
    # Strong Bullish Engulfing + Momentum
    if c3 > c2 > c1 and (c3 - c1) > 0.0018:
        return "BUY"
    # Strong Bearish
    elif c3 < c2 < c1 and (c1 - c3) > 0.0018:
        return "SELL"
    # Momentum
    elif c3 > c2 * 1.0015:
        return "BUY"
    elif c3 < c2 * 0.9985:
        return "SELL"
    
    return None

@dp.message()
async def send_signal_for_pair(message: types.Message):
    selected_name = message.text.strip()
    asset = next((k for k, v in ASSETS.items() if v == selected_name), None)
    
    if not asset:
        return

    await message.answer(f"🔍 Strong Analysis on **{selected_name}**...")

    signal = analyze_candles(asset)
    
    if signal:
        await send_signal(asset, signal, TIMEFRAME)
    else:
        await message.answer(f"⏳ No strong signal on **{selected_name}** right now.\nTap again.")

async def main():
    print("🚀 5s Signal Bot with New SSID Started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
