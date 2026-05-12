import asyncio
import json
import websocket
import threading
import time
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import ASSETS, active_assets, TIMEFRAME
from telegram_handler import send_signal

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# ====================== YOUR FULL SSID ======================
POCKET_SSID = '42["auth",{"session":"a:4:{s:10:\\"session_id\\";s:32:\\"5d42209a255eb7a6afa8369c692496b6\\";s:10:\\"ip_address\\";s:13:\\"102.249.74.12\\";s:10:\\"user_agent\\";s:117:\\"Mozilla/5.0 (Linux; Android 10; EVE-LX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36\\";s:13:\\"last_activity\\";i:1778507318;}80097a7ea66ab80609ad5ddeb0cf17b4","isDemo":0,"uid":130884208,"platform":3,"isFastHistory":true,"isOptimized":true}]'
# ========================================================

# Global storage
candles_data = {}
ws_client = None

# ====================== TELEGRAM MENU ======================

def get_assets_keyboard():
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(row_width=1)
    for symbol, name in ASSETS.items():
        status = "✅" if symbol in active_assets else "⬜"
        kb.add(InlineKeyboardButton(
            text=f"{status} {name}", 
            callback_data=f"toggle_{symbol}"
        ))
    kb.add(InlineKeyboardButton("🔄 Refresh", callback_data="refresh"))
    return kb

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🚀 **Pocket Option OTC Signal Bot**\n\n"
        "✅ Bot is Online & Connected!\n"
        "Use buttons below to toggle assets:",
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
    await callback.answer("✅ Updated")

@dp.callback_query(lambda c: c.data == "refresh")
async def refresh(callback: types.CallbackQuery):
    await callback.answer("🔄 Checking signals...")

# ====================== WEBSOCKET ======================

def on_ws_message(ws, message):
    try:
        data = json.loads(message)
        if isinstance(data, list):
            print(f"📡 Received: {data[0] if len(data) > 0 else 'unknown'}")
    except Exception as e:
        pass

def on_ws_open(ws):
    print("✅ WebSocket Connected Successfully!")
    for asset in list(active_assets):
        try:
            sub_msg = json.dumps(["subscribe", "candles", {"asset": asset, "period": TIMEFRAME}])
            ws.send(sub_msg)
            time.sleep(0.3)
        except:
            pass

def start_websocket():
    global ws_client
    try:
        ws_client = websocket.WebSocketApp(
            "wss://api.pocketoption.com/signal/v1",
            header={"Cookie": f"ssid={POCKET_SSID}"},
            on_open=on_ws_open,
            on_message=on_ws_message,
            on_error=lambda ws, err: print(f"WS Error: {err}"),
            on_close=lambda ws, *a: print("WebSocket Closed - Reconnecting...")
        )
        ws_client.run_forever()
    except Exception as e:
        print(f"WebSocket Start Failed: {e}")

# ====================== SIGNAL ENGINE ======================

async def signal_engine():
    print("🚀 Signal Engine Started...")
    while True:
        for asset in list(active_assets):
            try:
                if asset in candles_data and len(candles_data[asset]) > 15:
                    signal = generate_signal(candles_data[asset])
                    if signal:
                        await send_signal(asset, signal)
                        print(f"🚨 SIGNAL SENT: {asset} → {signal}")
            except:
                pass
        await asyncio.sleep(12)

# ====================== MAIN ======================

async def main():
    print("Starting Pocket Option OTC Bot with Full SSID...")
    
    # Start WebSocket in background
    threading.Thread(target=start_websocket, daemon=True).start()
    
    # Start signal checker
    asyncio.create_task(signal_engine())
    
    # Start Telegram bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
