import asyncio
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from api_pocket import AsyncPocketOptionClient
from config import ASSETS, active_assets, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from strategy import generate_signal
from telegram_handler import send_signal, get_assets_keyboard

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

client = None

# ====================== YOUR AUTH DATA ======================
SSID = '42["auth",{"session":"a:4:{s:10:\\"session_id\\";s:32:\\"5d42209a255eb7a6afa8369c692496b6\\";s:10:\\"ip_address\\";s:13:\\"102.249.74.12\\";s:10:\\"user_agent\\";s:117:\\"Mozilla/5.0 (Linux; Android 10; EVE-LX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36\\";s:13:\\"last_activity\\";i:1778507318;}80097a7ea66ab80609ad5ddeb0cf17b4","isDemo":0,"uid":130884208,"platform":3,"isFastHistory":true,"isOptimized":true}]'
# ====================== TELEGRAM COMMANDS ======================

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🚀 **Pocket Option OTC Signal Bot**\n\n"
        "✅ Connected & Running!\n"
        "Tap buttons below to enable/disable assets:",
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
    await callback.answer(f"{'✅ Activated' if symbol in active_assets else '❌ Deactivated'}")

@dp.callback_query(lambda c: c.data == "refresh")
async def refresh(callback: types.CallbackQuery):
    await callback.answer("🔄 Scanning for signals...")

# ====================== SIGNAL ENGINE ======================

async def signal_engine():
    global client
    client = AsyncPocketOptionClient(ssid=SSID, is_demo=False)  # is_demo=False because your data shows real account
    await client.connect()
    print("✅ Successfully connected to Pocket Option!")

    while True:
        current_assets = list(active_assets)
        for asset in current_assets:
            try:
                candles = await client.get_candles(asset, count=100)
                if not candles or len(candles) < 30:
                    continue

                df = pd.DataFrame(candles)
                df = df[['open', 'high', 'low', 'close']].astype(float)

                signal = generate_signal(df)
                if signal:
                    await send_signal(asset, signal)
                    print(f"🚨 SIGNAL SENT → {asset} | {signal}")
            except Exception as e:
                print(f"Error on {asset}: {e}")

        await asyncio.sleep(8)

# ====================== RUN ======================

async def main():
    print("Starting Pocket Option OTC Bot with Asset Menu...")
    asyncio.create_task(signal_engine())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
