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
    
    if direction == "BUY":
        signal_text = "BUY SIGNAL!"
        arrow = "↑"
        rocket = "🚀"
        color_emoji = "🟢"
    else:
        signal_text = "SELL SIGNAL!"
        arrow = "↓"
        rocket = "🔻"
        color_emoji = "🔴"

    message = f"""
{arrow} **{signal_text}** {rocket}

**Enter NOW** 🔥

{flag_name}
    """.strip()

    await bot.send_message(
        TELEGRAM_CHAT_ID, 
        message, 
        parse_mode="Markdown"
  )
