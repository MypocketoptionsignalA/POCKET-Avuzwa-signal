import asyncio
import logging
import random
from datetime import datetime
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, POCKET_SSID, DEFAULT_AMOUNT, USE_DEMO, TIMEFRAMES
from pocket_api import PocketOptionClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAST = pytz.timezone('Africa/Johannesburg')

# Expanded Pairs
PAIRS = [
    "🇺🇸/🇯🇵 USD/JPY OTC",
    "🇬🇧/🇺🇸 GBP/USD OTC",
    "🇬🇧/🇯🇵 GBP/JPY OTC",
    "🇪🇺/🇺🇸 EUR/USD OTC",
    "🇦🇺/🇺🇸 AUD/USD OTC",
    "🇦🇺/🇯🇵 AUD/JPY OTC",
    "🇪🇺/🇬🇧 EUR/GBP OTC",
    "🇺🇸/🇨🇭 USD/CHF OTC",
    "🇬🇧/🇦🇺 GBP/AUD OTC",
    "🇦🇺/🇨🇦 AUD/CAD OTC",
    "🇦🇺/🇨🇭 AUD/CHF OTC",
    "🇦🇪/🇨🇳 AED/CNY OTC"
]

CLEAN_PAIRS = {p: p.split()[-3] + "/" + p.split()[-1] if len(p.split()) > 2 else p for p in PAIRS}

po_api = None

async def init_pocket_api():
    global po_api
    if POCKET_SSID:
        po_api = PocketOptionClient(POCKET_SSID, is_demo=USE_DEMO)
        po_api.connect()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    await update.message.reply_text("Bot Ready! Use /signal")

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only")
        return

    keyboard = [[KeyboardButton(pair)] for pair in PAIRS]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    await update.message.reply_text("📍 Select Pair:", reply_markup=reply_markup)

async def pair_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    selected = update.message.text.strip()
    if selected not in PAIRS:
        return

    display_pair = selected
    clean_pair = CLEAN_PAIRS.get(display_pair, display_pair)

    context.user_data["display_pair"] = display_pair
    context.user_data["clean_pair"] = clean_pair

    # Timeframe buttons
    tf_keyboard = [[InlineKeyboardButton(f"{tf}", callback_data=f"time_{tf}")] for tf in TIMEFRAMES.keys()]
    await update.message.reply_text(f"Choose Timeframe for {display_pair}", reply_markup=InlineKeyboardMarkup(tf_keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        return

    data = query.data
    if data.startswith("time_"):
        tf = data.replace("time_", "")
        display_pair = context.user_data.get("display_pair")
        clean_pair = context.user_data.get("clean_pair")
        expiration = TIMEFRAMES[tf]

        direction = random.choice(["call", "put"])

        if direction == "call":
            signal = f"↑ BUY SIGNAL!\nEnter NOW 🔥\n\n{display_pair}"
            emoji = "🚀"
        else:
            signal = f"↓ SELL SIGNAL!\nEnter NOW 🔥\n\n{display_pair}"
            emoji = "🚨"

        await query.edit_message_text(signal)

        # Extra pair message like original bot
        await query.message.reply_text(display_pair)

        # Try real trade silently
        if po_api and getattr(po_api, 'connected', False):
            po_api.buy(clean_pair, DEFAULT_AMOUNT, direction, expiration)

        await asyncio.sleep(expiration + 3)
        await query.message.reply_text("Signal expired.")

async def main():
    await init_pocket_api()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, pair_message_handler))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 Bot Started - Matching A Bot Style")

    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
