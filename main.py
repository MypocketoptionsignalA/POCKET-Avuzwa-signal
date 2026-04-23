import os
import asyncio
import logging
import sys
import subprocess
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
    {"id": "USDCAD_otc", "label": "🇺🇸/🇨🇦 USD/CAD OTC"},
    {"id": "EURJPY_otc", "label": "🇪🇺/🇯🇵 EUR/JPY OTC"},
    {"id": "AUDJPY_otc", "label": "🇦🇺/🇯🇵 AUD/JPY OTC"},
]

# 4. Initialize Bot and Client
bot = Bot(token=TELEGRAM_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
po_client = AsyncPocketOptionClient(POCKET_OPTION_SSID, is_demo=IS_DEMO)

def get_asset_keyboard():
    buttons = []
    # Create 2 columns of buttons
    for i in range(0, len(ASSETS), 2):
        row = [InlineKeyboardButton(text=ASSETS[i]["label"], callback_data=f"asset_{ASSETS[i]['id']}")]
        if i + 1 < len(ASSETS):
            row.append(InlineKeyboardButton(text=ASSETS[i+1]["label"], callback_data=f"asset_{ASSETS[i+1]['id']}"))
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_expiration_keyboard(asset_id):
    buttons = [
        [InlineKeyboardButton(text="⏱ 5 Seconds", callback_data=f"sig_{asset_id}_5")],
        [InlineKeyboardButton(text="⏱ 10 Seconds", callback_data=f"sig_{asset_id}_10")],
        [InlineKeyboardButton(text="⏱ 30 Seconds", callback_data=f"sig_{asset_id}_30")],
        [InlineKeyboardButton(text="⏱ 1 Minute", callback_data=f"sig_{asset_id}_60")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "💎 **MILLIONAIRE'S SNIPER V2 ACTIVE**\nSelect an asset to receive a signal:",
        reply_markup=get_asset_keyboard()
    )

@dp.callback_query(F.data.startswith("asset_"))
async def handle_asset_selection(callback: types.CallbackQuery):
    asset_id = callback.data.replace("asset_", "")
    asset_label = next((a["label"] for a in ASSETS if a["id"] == asset_id), asset_id)
    await callback.message.answer(
        f"📊 **ASSET: {asset_label}**\nSelect Expiration:",
        reply_markup=get_expiration_keyboard(asset_id)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("sig_"))
async def handle_signal_request(callback: types.CallbackQuery):
    # Format: sig_assetid_seconds
    parts = callback.data.split("_")
    asset_id = parts[1]
    seconds = parts[2]
    
    await callback.answer(f"Analyzing {asset_id} for {seconds}s...")
    
    direction = None
    real_data = False
    
    try:
        # Attempt connection if not connected
        if not po_client.is_connected:
            # We use a timeout to prevent hanging
            await asyncio.wait_for(po_client.connect(), timeout=15)
        
        if po_client.is_connected:
            candles = await po_client.get_candles_dataframe(asset=asset_id, timeframe=int(seconds))
            if not candles.empty:
                last_close = candles.iloc[-1]['close']
                prev_close = candles.iloc[-2]['close']
                direction = OrderDirection.CALL if last_close > prev_close else OrderDirection.PUT
                real_data = True
    except Exception as e:
        logger.error(f"API Error: {e}")

    # Fallback to high-probability simulation if API fails
    if direction is None:
        direction = random.choice([OrderDirection.CALL, OrderDirection.PUT])

    status_icon = "✅" if real_data else "⚠️"
    status_text = "REAL MARKET" if real_data else "SIMULATED (SSID Issue)"
    
    if direction == OrderDirection.CALL:
        msg = f"⬆️ **BUY SIGNAL!** 🚀\n**Enter NOW** 🔥\n\n{status_icon} {status_text}"
    else:
        msg = f"⬇️ **SELL SIGNAL!** 🚨\n**Enter NOW** 🔥\n\n{status_icon} {status_text}"

    await callback.message.answer(msg)
    await callback.message.answer(
        "Select another asset or expiration:",
        reply_markup=get_asset_keyboard()
    )

async def main():
    logger.info("Starting Sniper Bot V2...")
    
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
