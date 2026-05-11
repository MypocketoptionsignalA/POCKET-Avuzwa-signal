from aiogram import Bot, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ASSETS, active_assets

bot = Bot(token=TELEGRAM_TOKEN)

async def send_signal(asset: str, direction: str):
    flag_name = ASSETS.get(asset, asset)
    
    if direction == "BUY":
        emoji = "🟢"
        text = "BUY SIGNAL!"
        rocket = "🚀"
    else:
        emoji = "🔴"
        text = "SELL SIGNAL!"
        rocket = "🔻"

    message = f"""
{emoji} **{text}** {rocket}

**Enter NOW** 🔥

{flag_name}
    """.strip()

    await bot.send_message(TELEGRAM_CHAT_ID, message, parse_mode="Markdown")

def get_assets_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    for symbol, name in ASSETS.items():
        status = "✅" if symbol in active_assets else "⬜"
        keyboard.add(InlineKeyboardButton(
            text=f"{status} {name}",
            callback_data=f"toggle_{symbol}"
        ))
    keyboard.add(InlineKeyboardButton("🔄 Refresh Signals", callback_data="refresh"))
    return keyboard
