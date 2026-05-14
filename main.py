import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi import FastAPI, Request
import uvicorn
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

app = FastAPI()

# Simple Webhook Endpoint
@app.post("/webhook")
async def tradingview_webhook(request: Request):
    data = await request.json()
    
    symbol = data.get("symbol", "UNKNOWN")
    direction = data.get("direction", "BUY").upper()
    timeframe = data.get("timeframe", 5)
    
    message = f"""
🔴 **TradingView Signal**

**{direction} SIGNAL!** {'🚀' if direction == "BUY" else '🔻'}

Enter NOW 🔥

{symbol} OTC
⏳ Expiry: {timeframe} seconds
    """.strip()
    
    await bot.send_message(TELEGRAM_CHAT_ID, message)
    return {"status": "ok"}

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🚀 **TradingView + Pocket Option Bot**\n\n"
        "✅ Webhook is Active!\n"
        "Now create alerts on TradingView"
    )

async def main():
    print("🚀 Bot Started - Waiting for TradingView Webhooks...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Run both Telegram bot and Webhook server
    import threading
    threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000), daemon=True).start()
    asyncio.run(main())
