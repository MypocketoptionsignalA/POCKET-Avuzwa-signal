import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from fastapi import FastAPI, Request
import uvicorn
import threading

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
app = FastAPI()

# ====================== TRADINGVIEW WEBHOOK ======================

@app.post("/webhook")
async def tradingview_webhook(request: Request):
    try:
        data = await request.json()
        
        symbol = data.get("symbol", "UNKNOWN OTC")
        direction = data.get("direction", "BUY").upper()
        timeframe = data.get("timeframe", 5)
        
        emoji = "🟢" if direction == "BUY" else "🔴"
        rocket = "🚀" if direction == "BUY" else "🔻"
        
        message = f"""
{emoji} **{direction} SIGNAL!** {rocket}

**Enter NOW** 🔥

{symbol}

⏳ **Expiry: {timeframe} seconds**
        """.strip()

        await bot.send_message(TELEGRAM_CHAT_ID, message, parse_mode="Markdown")
        print(f"Signal Sent: {direction} {symbol}")
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"Webhook Error: {e}")
        return {"status": "error"}

# ====================== TELEGRAM COMMANDS ======================

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🚀 **TradingView Webhook Bot**\n\n"
        "✅ Ready to receive signals from TradingView!\n\n"
        "Create alert on TradingView with Webhook URL:\n"
        "https://your-railway-app.railway.app/webhook"
    )

async def main():
    print("🚀 TradingView Webhook Bot Started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Run Webhook server in background
    threading.Thread(
        target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000),
        daemon=True
    ).start()
    
    asyncio.run(main())
