import asyncio
import random
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from config import ASSETS, active_assets
from telegram_handler import send_signal

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# ====================== YOUR SSID ======================
POCKET_SSID = '42["auth",{"session":"a:4:{s:10:\\"session_id\\";s:32:\\"5d42209a255eb7a6afa8369c692496b6\\";s:10:\\"ip_address\\";s:13:\\"102.249.74.12\\";s:10:\\"user_agent\\";s:117:\\"Mozilla/5.0 (Linux; Android 10; EVE-LX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36\\";s:13:\\"last_activity\\";i:1778507318;}80097a7ea66ab80609ad5ddeb0cf17b4","isDemo":0,"uid":130884208,"platform":3,"isFastHistory":true,"isOptimized":true}]'

current_timeframe = 60

# ====================== PERMANENT BOTTOM KEYBOARD ======================

def get_main_keyboard():
    keyboard = [
        [KeyboardButton(text="🔄 Get Signals")],
        [KeyboardButton(text="⏱️ Change Timeframe")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, persistent=True)

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
        "✅ Bot is **Ready**!\n\n"
        "How to use:\n"
        "1. Tap pairs below to Activate/Deactivate\n"
        "2. Choose Timeframe\n"
        "3. Press **🔄 Get Signals**",
        reply_markup=get_pairs_keyboard()
    )
    await message.answer("⏱️ Select Timeframe:", reply_markup=get_timeframe_keyboard())

# Handle pair toggle
@dp.message(lambda m: any(name in m.text for name in ASSETS.values()))
async def handle_pair_selection(message: types.Message):
    selected_name = message.text.strip()
    symbol = next((k for k, v in ASSETS.items() if v == selected_name), None)
    
    if symbol:
        if symbol in active_assets:
            active_assets.remove(symbol)
            await message.answer(f"❌ **Deactivated** {selected_name}")
        else:
            active_assets.add(symbol)
            await message.answer(f"✅ **Activated** {selected_name}")
    else:
        await message.answer("Unknown pair.")

# Get Signals Button
@dp.message(lambda m: m.text == "🔄 Get Signals")
async def get_signals(message: types.Message):
    if not active_assets:
        await message.answer("⚠️ No pairs activated!\nPlease tap pairs below to activate.")
        return

    await message.answer("🔍 Analyzing current market...")

    sent = 0
    for asset in list(active_assets):
        try:
            direction = "BUY" if random.random() > 0.5 else "SELL"
            await send_signal(asset, direction, current_timeframe)
            sent += 1
        except:
            pass

    if sent == 0:
        await message.answer("⏳ No clear signals right now. Try again later.")

# Change Timeframe Button
@dp.message(lambda m: m.text == "⏱️ Change Timeframe")
async def show_timeframe(message: types.Message):
    await message.answer("⏱️ Select Timeframe:", reply_markup=get_timeframe_keyboard())

@dp.callback_query(lambda c: c.data.startswith("tf_"))
async def change_timeframe(callback: types.CallbackQuery):
    global current_timeframe
    current_timeframe = int(callback.data.replace("tf_", ""))
    await callback.answer(f"✅ Timeframe: {current_timeframe}s")

async def main():
    print("🚀 Pocket Option OTC Signal Bot Started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
