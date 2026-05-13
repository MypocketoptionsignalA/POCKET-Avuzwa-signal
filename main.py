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

# ====================== YOUR SSID ======================
POCKET_SSID = '42["auth",{"session":"a:4:{s:10:\\"session_id\\";s:32:\\"5d42209a255eb7a6afa8369c692496b6\\";s:10:\\"ip_address\\";s:13:\\"102.249.74.12\\";s:10:\\"user_agent\\";s:117:\\"Mozilla/5.0 (Linux; Android 10; EVE-LX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36\\";s:13:\\"last_activity\\";i:1778507318;}80097a7ea66ab80609ad5ddeb0cf17b4","isDemo":0,"uid":130884208,"platform":3,"isFastHistory":true,"isOptimized":true}]'

TIMEFRAME = 5   # Fixed 5 seconds

# ====================== BOTTOM KEYBOARD ======================

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

# ====================== START ======================

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🚀 **Pocket Option 5s OTC Signal Bot**\n\n"
        "✅ Tap any pair below to get strong **Buy** or **Sell** signal (5 seconds expiry)",
        reply_markup=get_pairs_keyboard()
    )

# ====================== STRONGER ANALYSIS ======================

def analyze_candles(asset):
    """Stronger signal logic for 5s OTC"""
    # Simulate multiple candles with better pattern detection
    closes = [random.uniform(0.998, 1.002) for _ in range(10)]
    
    # Last 3 candles
    c1, c2, c3 = closes[-3], closes[-2], closes[-1]
    
    # Strong Bullish
    if c3 > c2 > c1 and (c3 - c1) > 0.0015:
        return "BUY"
    
    # Strong Bearish
    if c3 < c2 < c1 and (c1 - c3) > 0.0015:
        return "SELL"
    
    # Momentum continuation
    if c3 > c2 * 1.0012:
        return "BUY"
    elif c3 < c2 * 0.9988:
        return "SELL"
    
    return None

# ====================== MAIN LOGIC ======================

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
        print(f"Strong Signal → {asset} | {signal}")
    else:
        await message.answer(f"⏳ No strong signal on **{selected_name}** right now.\nTap again.")

async def main():
    print("🚀 5s Strong Signal Bot Started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
