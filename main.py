import asyncio
import json
import websocket
import threading
import time
import os
import random
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import ASSETS, active_assets
from telegram_handler import send_signal
from strategy import generate_signal

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# ====================== YOUR SSID ======================
POCKET_SSID = '42["auth",{"session":"a:4:{s:10:\\"session_id\\";s:32:\\"5d42209a255eb7a6afa8369c692496b6\\";s:10:\\"ip_address\\";s:13:\\"102.249.74.12\\";s:10:\\"user_agent\\";s:117:\\"Mozilla/5.0 (Linux; Android 10; EVE-LX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36\\";s:13:\\"last_activity\\";i:1778507318;}80097a7ea66ab80609ad5ddeb0cf17b4","isDemo":0,"uid":130884208,"platform":3,"isFastHistory":true,"isOptimized":true}]'

candles_data = {}
current_timeframe = 60

# ====================== KEYBOARDS ======================

def get_assets_keyboard():
    buttons = []
    for symbol, name in ASSETS.items():
        status = "✅" if symbol in active_assets else "⬜"
        buttons.append([InlineKeyboardButton(text=f"{status} {name}", callback_data=f"toggle_{symbol}")])
    buttons.append([InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_timeframe_keyboard():
    tfs = [5, 10, 15, 30, 60]
    buttons = []
    row = []
    for tf in tfs:
        status = "✅" if tf == current_timeframe else ""
        row.append(InlineKeyboardButton(text=f"{status}{tf}s", callback_data=f"tf_{tf}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ====================== COMMANDS ======================

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🚀 **Pocket Option OTC Signal Bot**\n\n"
        "✅ Bot is **Active**!\n"
        "Select pairs & timeframe below:",
        reply_markup=get_assets_keyboard()
    )
    await message.answer("⏱️ Select Timeframe:", reply_markup=get_timeframe_keyboard())

@dp.callback_query(lambda c: c.data.startswith("toggle_"))
async def toggle_asset(callback: types.CallbackQuery):
    symbol = callback.data.replace("toggle_", "")
    if symbol in active_assets:
        active_assets.remove(symbol)
    else:
        active_assets.add(symbol)
    await callback.message.edit_reply_markup(reply_markup=get_assets_keyboard())
    await callback.answer("Updated ✅")

@dp.callback_query(lambda c: c.data.startswith("tf_"))
async def change_timeframe(callback: types.CallbackQuery):
    global current_timeframe
    current_timeframe = int(callback.data.replace("tf_", ""))
    await callback.message.edit_reply_markup(reply_markup=get_timeframe_keyboard())
    await callback.answer(f"✅ {current_timeframe}s")

# ====================== SIGNAL ENGINE (For Testing) ======================

async def signal_engine():
    print("🚀 Auto Signal Generator Started...")
    while True:
        for asset in list(active_assets):
            try:
                # Generate random signals for testing (replace later with real logic)
                if random.random() < 0.25:   # 25% chance to send signal
                    direction = "BUY" if random.random() > 0.5 else "SELL"
                    await send_signal(asset, direction, current_timeframe)
                    print(f"Signal Sent → {asset} | {direction}")
            except:
                pass
        await asyncio.sleep(15)   # Send signals every \~15 seconds when active

async def main():
    print("🚀 Bot Starting...")
    asyncio.create_task(signal_engine())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
