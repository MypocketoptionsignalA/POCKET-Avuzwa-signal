import asyncio
import json
import websocket
import threading
import time
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from config import ASSETS, active_assets
from telegram_handler import send_signal
from strategy import generate_signal

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

POCKET_SSID = '42["auth",{"session":"a:4:{s:10:\\"session_id\\";s:32:\\"5d42209a255eb7a6afa8369c692496b6\\";s:10:\\"ip_address\\";s:13:\\"102.249.74.12\\";s:10:\\"user_agent\\";s:117:\\"Mozilla/5.0 (Linux; Android 10; EVE-LX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36\\";s:13:\\"last_activity\\";i:1778507318;}80097a7ea66ab80609ad5ddeb0cf17b4","isDemo":0,"uid":130884208,"platform":3,"isFastHistory":true,"isOptimized":true}]'

candles_data = {}
current_timeframe = 60

# ====================== KEYBOARDS ======================

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

def get_timeframe_keyboard():
    tfs = [5, 10, 15, 30, 60]
    buttons = [[InlineKeyboardButton(text=f"{tf}s", callback_data=f"tf_{tf}")] for tf in tfs]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ====================== COMMANDS ======================

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🚀 **Pocket Option OTC Signal Bot**\n\n"
        "✅ Bot is Ready!\n"
        "• Tap pairs below to activate/deactivate\n"
        "• Choose timeframe\n"
        "• Type **/signal** to get fresh signals",
        reply_markup=get_pairs_keyboard()
    )
    await message.answer("⏱️ Select Timeframe:", reply_markup=get_timeframe_keyboard())

# Toggle pairs from bottom keyboard
@dp.message()
async def handle_pair(message: types.Message):
    selected = message.text
    symbol = next((k for k, v in ASSETS.items() if v == selected), None)
    if symbol:
        if symbol in active_assets:
            active_assets.remove(symbol)
            await message.answer(f"❌ **Deactivated** {selected}")
        else:
            active_assets.add(symbol)
            await message.answer(f"✅ **Activated** {selected}")
    else:
        await message.answer("Unknown pair. Use the buttons below.")

@dp.callback_query(lambda c: c.data.startswith("tf_"))
async def change_timeframe(callback: types.CallbackQuery):
    global current_timeframe
    current_timeframe = int(callback.data.replace("tf_", ""))
    await callback.answer(f"✅ Timeframe: {current_timeframe}s")

# ====================== MANUAL SIGNAL REQUEST ======================

@dp.message(Command("signal"))
async def manual_signal(message: types.Message):
    if not active_assets:
        await message.answer("⚠️ Please activate at least one pair first!")
        return
    
    await message.answer("🔍 Analyzing current candles...")
    
    for asset in list(active_assets):
        try:
            # For now using dummy data (we'll improve with real candles later)
            signal = generate_signal([{"open":1,"close":1.5}] * 10)  # Placeholder
            if signal:
                await send_signal(asset, signal, current_timeframe)
            else:
                await message.answer(f"⏳ No clear signal for {ASSETS[asset]} right now.")
        except:
            pass

    await message.answer("✅ Signal check completed!")

async def main():
    print("🚀 Manual Signal Bot Started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
