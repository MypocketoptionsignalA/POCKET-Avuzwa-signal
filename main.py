import asyncio
import pandas as pd
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from api_pocket import AsyncPocketOptionClient

load_dotenv()

from config import ASSETS, active_assets
from strategy import generate_signal
from telegram_handler import send_signal, get_assets_keyboard

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

SSID = os.getenv("POCKET_SSID")

# ====================== TELEGRAM COMMANDS ======================

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🚀 **Pocket Option OTC Signal Bot**\n\n"
        "✅ Bot is Online!\n"
        "Use buttons below to enable/disable assets:",
        reply_markup=get_assets_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith("toggle_"))
async def toggle_asset(callback: types.CallbackQuery):
    symbol = callback.data.replace("toggle_", "")
    if symbol in active_assets:
        active_assets.remove(symbol)
    else:
        active_assets.add(symbol)
    
    await callback.message.edit_reply_markup(reply_markup=get_assets_keyboard())
    await callback.answer("Updated!")

# ====================== SIGNAL ENGINE ======================

async def signal_engine():
    global client
    client = AsyncPocketOptionClient(ssid=SSID, is_demo=False)
    await client.connect()
    print("✅ Connected to Pocket Option")

    while True:
        for asset in list(active_assets):
            try:
                candles = await client.get_candles(asset, count=100)
                if len(candles) < 30:
                    continue
                df = pd.DataFrame(candles)[['open', 'high', 'low', 'close']].astype(float)
                
                signal = generate_signal(df)
                if signal:
                    await send_signal(asset, signal)
            except Exception as e:
                print(f"Error {asset}: {e}")
        await asyncio.sleep(8)

async def main():
    asyncio.create_task(signal_engine())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
