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

PAIRS = ["USD/JPY OTC", "GBP/USD OTC", "GBP/JPY OTC", "EUR/USD OTC", "AUD/USD OTC"]

po_api = None

async def init_pocket_api():
    global po_api
    if not POCKET_SSID:
        return False
    po_api = PocketOptionClient(POCKET_SSID, is_demo=USE_DEMO)
    return po_api.connect()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Unauthorized")
        return
    await update.message.reply_text("Bot Ready! Send /signal")

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Admin only")
        return

    keyboard = [[KeyboardButton(p)] for p in PAIRS]
    await update.message.reply_text("Select Pair", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def pair_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    selected = update.message.text
    if selected not in PAIRS:
        return

    context.user_data["pair"] = selected

    tf_keyboard = [[InlineKeyboardButton(tf, callback_data=f"time_{tf}")] for tf in TIMEFRAMES.keys()]
    await update.message.reply_text("Choose Timeframe", reply_markup=InlineKeyboardMarkup(tf_keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        return

    if query.data.startswith("time_"):
        tf = query.data.replace("time_", "")
        pair = context.user_data.get("pair")

        direction = random.choice(["call", "put"])
        signal = f"{'BUY' if direction == 'call' else 'SELL'} SIGNAL! Enter NOW\n\n{pair}"

        await query.edit_message_text(signal)

        if po_api and po_api.connected:
            po_api.buy(pair, DEFAULT_AMOUNT, direction, TIMEFRAMES[tf])

        await asyncio.sleep(TIMEFRAMES[tf] + 5)
        await query.message.reply_text("Signal expired.")

async def main():
    await init_pocket_api()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, pair_message_handler))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot started")

    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
