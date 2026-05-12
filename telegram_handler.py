from aiogram import Bot
from config import ASSETS

bot = Bot(token=TELEGRAM_TOKEN)

async def send_signal(asset: str, direction: str):
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
