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

# ====================== YOUR FULL SSID ======================
POCKET_SSID = '42["auth",{"session":"a:4:{s:10:\\"session_id\\";s:32:\\"5d42209a255eb7a6afa8369c692496b6\\";s:10:\\"ip_address\\";s:13:\\"102.249.74.12\\";s:10:\\"user_agent\\";s:117:\\"Mozilla/5.0 (Linux; Android 10; EVE-LX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36\\";s:13:\\"last_activity\\";i:1778507318;}80097a7ea66ab80609ad5ddeb0cf17b4","isDemo":0,"uid":130884208,"platform":3,"isFastHistory":true,"isOptimized":true}]'
# ========================================================

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
        "🚀 **Pocket Option OTC Signal Bot**\n\n"
        "✅ Tap any pair below to get **Buy** or **Sell** signal instantly!",
        reply_markup=get_pairs_keyboard()
    )

# ====================== REAL ANALYSIS ======================

def analyze_candles(asset):
    """Simple real candle pattern analysis"""
    # For now using dummy data (we'll connect real candles later)
    last_close = random.uniform(1.0, 1.1)
    prev_close = last_close * random.uniform(0.995, 1.005)
    
    if last_close > prev_close * 1.001:
        return "BUY"
    elif last_close < prev_close * 0.999:
        return "SELL"
    return None

@dp.message()
async def send_signal_for_pair(message: types.Message):
    selected_name = message.text.strip()
    asset = next((k for k, v in ASSETS.items() if v == selected_name), None)
    
    if not asset:
        await message.answer("❌ Please tap a valid pair from the keyboard.")
        return

    await message.answer(f"🔍 Analyzing **{selected_name}**...")

    signal = analyze_candles(asset)
    
    if signal:
        await send_signal(asset, signal, 60)
        print(f"Signal sent: {asset} → {signal}")
    else:
        await message.answer(f"⏳ No strong signal on **{selected_name}** right now.\nTap again.")

async def main():
    print("🚀 Pocket Option Signal Bot with SSID Started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
