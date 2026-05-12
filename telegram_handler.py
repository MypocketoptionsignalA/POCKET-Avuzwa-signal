import os
from dotenv import load_dotenv
from aiogram import Bot

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

async def send_signal(asset: str, direction: str):
    from config import ASSETS
    flag_name = ASSETS.get(asset, asset)
    
    emoji = "🟢" if direction == "BUY" else "🔴"
    text = "BUY SIGNAL!" if direction == "BUY" else "SELL SIGNAL!"
    rocket = "🚀" if direction == "BUY" else "🔻"

    message = f"""
{emoji} **{text}** {rocket}

**Enter NOW** 🔥

{flag_name}
    """.strip()

    await bot.send_message(TELEGRAM_CHAT_ID, message, parse_mode="Markdown")
