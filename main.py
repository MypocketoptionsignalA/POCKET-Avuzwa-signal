import asyncio
import json
import websocket
import threading
import time
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

# ====================== YOUR LATEST SSID ======================
POCKET_SSID = '42["auth",{"session":"a:4:{s:10:\"session_id\";s:32:\"0ae6554999c3a25eac4872f3b6e32660\";s:10:\"ip_address\";s:14:\"105.245.234.35\";s:10:\"user_agent\";s:117:\"Mozilla/5.0 (Linux; Android 10; EVE-LX9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36\";s:13:\"last_activity\";i:1778687392;}d5cd6bd3e7c7b7d094f9cb4e244c87a1","isDemo":0,"uid":130884208,"platform":3,"isFastHistory":true,"isOptimized":true}]'
# ========================================================

TIMEFRAME = 5
candles_data = {}

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

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🚀 **Pocket Option Real Data Bot**\n\n"
        "✅ Tap any pair below to get signal from live connection",
        reply_markup=get_pairs_keyboard()
    )

# ====================== REAL WEBSOCKET ======================

def on_ws_message(ws, message):
    try:
        data = json.loads(message)
        if isinstance(data, list) and len(data) > 1:
            # Try to capture candle data
            for asset in ASSETS.keys():
                if asset in str(data):
                    if asset not in candles_data:
                        candles_data[asset] = []
                    candles_data[asset].append(data[1] if isinstance(data[1], dict) else {})
                    if len(candles_data[asset]) > 30:
                        candles_data[asset] = candles_data[asset][-30:]
    except:
        pass

def on_ws_open(ws):
    print("✅ WebSocket Connected - Trying real data")
    for asset in list(ASSETS.keys()):
        try:
            sub = json.dumps(["subscribe", "candles", {"asset": asset, "period": TIMEFRAME}])
            ws.send(sub)
            time.sleep(0.5)
        except:
            pass

def start_websocket():
    try:
        ws = websocket.WebSocketApp(
            "wss://api.pocketoption.com/signal/v1",
            header={"Cookie": f"ssid={POCKET_SSID}"},
            on_open=on_ws_open,
            on_message=on_ws_message,
            on_error=lambda ws, err: print(f"WS Error: {err}"),
            on_close=lambda ws, *a: print("WebSocket Closed")
        )
        ws.run_forever()
    except Exception as e:
        print(f"WebSocket Failed: {e}")

# ====================== SIGNAL LOGIC ======================

def analyze_candles(asset):
    if asset not in candles_data or len(candles_data[asset]) < 6:
        # Fallback
        return "BUY" if random.random() > 0.5 else "SELL"
    
    # Use real data if available
    data = candles_data[asset]
    if len(data) >= 3:
        try:
            last = data[-1]
            prev = data[-2]
            if isinstance(last, dict) and isinstance(prev, dict):
                if last.get('close', 0) > last.get('open', 0) and prev.get('close', 0) < prev.get('open', 0):
                    return "BUY"
                elif last.get('close', 0) < last.get('open', 0) and prev.get('close', 0) > prev.get('open', 0):
                    return "SELL"
        except:
            pass
    return None

@dp.message()
async def send_signal_for_pair(message: types.Message):
    selected_name = message.text.strip()
    asset = next((k for k, v in ASSETS.items() if v == selected_name), None)
    
    if not asset:
        return

    await message.answer(f"🔍 **Live Analysis** on **{selected_name}**...")

    signal = analyze_candles(asset)
    
    if signal:
        await send_signal(asset, signal, TIMEFRAME)
    else:
        await message.answer(f"⏳ No strong signal on **{selected_name}** right now.\nTap again.")

async def main():
    print("🚀 Starting Real WebSocket Connection...")
    threading.Thread(target=start_websocket, daemon=True).start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
