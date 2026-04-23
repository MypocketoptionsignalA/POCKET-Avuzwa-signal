import os
import asyncio
import logging
import sys
import subprocess
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from pocketoptionapi_async import AsyncPocketOptionClient, OrderDirection

# 1. Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger("SniperBot")

# 2. Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
POCKET_OPTION_SSID = os.getenv("POCKET_OPTION_SSID")
IS_DEMO = os.getenv("IS_DEMO", "False").lower() == "true"

# 3. Assets Configuration
ASSETS = [
    {"id": "USDJPY_otc", "label": "🇺🇸/🇯🇵 USD/JPY OTC"},
    {"id": "GBPUSD_otc", "label": "🇬🇧/🇺🇸 GBP/USD OTC"},
    {"id": "GBPJPY_otc", "label": "🇬🇧/🇯🇵 GBP/JPY OTC"},
    {"id": "EURUSD_otc", "label": "🇪🇺/🇺🇸 EUR/USD OTC"},
    {"id": "AUDUSD_otc", "label": "🇦🇺/🇺🇸 AUD/USD OTC"},
]

# 4. Initialize Bot and Client
bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
po_client = AsyncPocketOptionClient(POCKET_OPTION_SSID, is_demo=IS_DEMO)

def get_asset_reply_keyboard():
    # This creates the permanent keyboard at the bottom
    buttons = []
    for asset in ASSETS:
        buttons.append([KeyboardButton(text=asset["label"])])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_expiration_inline_keyboard(asset_label):
    # This shows the expiration options after an asset is clicked
    buttons = [
        [InlineKeyboardButton(text="⏱ 5 Seconds", callback_data=f"sig_{asset_label}_5")],
        [InlineKeyboardButton(text="⏱ 10 Seconds", callback_data=f"sig_{asset_label}_10")],
        [InlineKeyboardButton(text="⏱ 30 Seconds", callback_data=f"sig_{asset_label}_30")],
        [InlineKeyboardButton(text="⏱ 1 Minute", callback_data=f"sig_{asset_label}_60")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "💎 **MILLIONAIRE'S SNIPER V2 ACTIVE**\nSelect an asset from the keyboard below:",
        reply_markup=get_asset_reply_keyboard()
    )

@dp.message(F.text.in_([a["label"] for a in ASSETS]))
async def handle_asset_click(message: types.Message):
    asset_label = message.text
    await message.answer(
        f"📊 **ASSET: {asset_label}**\nSelect Expiration:",
        reply_markup=get_expiration_inline_keyboard(asset_label)
    )

@dp.callback_query(F.data.startswith("sig_"))
async def handle_signal_request(callback: types.CallbackQuery):
    # Format: sig_assetlabel_seconds
    parts = callback.data.split("_")
    asset_label = parts[1]
    seconds = parts[2]
    
    # Find the asset ID from the label
    asset_id = next((a["id"] for a in ASSETS if a["label"] == asset_label), "EURUSD_otc")
    
    await callback.answer(f"Analyzing {asset_label}...")
    
    direction = None
    real_data = False
    
    try:
        if not po_client.is_connected:
            await asyncio.wait_for(po_client.connect(), timeout=10)
        
        if po_client.is_connected:
            candles = await po_client.get_candles_dataframe(asset=asset_id, timeframe=int(seconds))
            if not candles.empty:
                last_close = candles.iloc[-1]['close']
                prev_close = candles.iloc[-2]['close']
                direction = OrderDirection.CALL if last_close > prev_close else OrderDirection.PUT
                real_data = True
    except Exception as e:
        logger.error(f"API Error: {e}")

    if direction is None:
        direction = random.choice([OrderDirection.CALL, OrderDirection.PUT])

    status_icon = "✅" if real_data else "⚠️"
    status_text = "REAL MARKET" if real_data else "SIMULATED (SSID Issue)"
    
    if direction == OrderDirection.CALL:
        msg = f"⬆️ **BUY SIGNAL!** 🚀\n**Enter NOW** 🔥\n\n{status_icon} {status_text}"
    else:
        msg = f"⬇️ **SELL SIGNAL!** 🚨\n**Enter NOW** 🔥\n\n{status_icon} {status_text}"

    await callback.message.answer(msg)

async def main():
    logger.info("Starting Sniper Bot with Reply Keyboard...")
    
    # Patch the library at runtime
    try:
        subprocess.run([sys.executable, "patch_api.py"], check=True)
    except:
        pass

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.critical(f"Polling failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
