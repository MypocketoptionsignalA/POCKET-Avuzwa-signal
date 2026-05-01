import asyncio
import logging
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

import requests  # For future real trading if needed

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Import config
from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, POCKET_SSID, DEFAULT_AMOUNT, DEFAULT_EXPIRATION

# List of common OTC pairs from your screenshot
PAIRS = ["USD/JPY OTC", "GBP/USD OTC", "GBP/JPY OTC", "EUR/USD OTC", "AUD/USD OTC"]

TIMEFRAMES = ["5s", "10s", "15s", "30s"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized. This bot is for admin only.")
        return
    
    await update.message.reply_text(
        "🚀 Pocket Option Signal Bot Ready!\n\n"
        "Commands:\n"
        "/signal - Send a new signal\n"
        "/help - Show help"
    )

async def send_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only.")
        return

    keyboard = []
    for pair in PAIRS:
        row = []
        for tf in TIMEFRAMES:
            row.append(InlineKeyboardButton(f"{pair} {tf}", callback_data=f"sig_{pair}_{tf}"))
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select Pair & Timeframe:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ Unauthorized.")
        return

    data = query.data.split("_")  # sig_PAIR_TIMEFRAME
    _, pair, timeframe = data

    # Random direction for demo (in real version you would use your strategy)
    direction = random.choice(["🔻 SELL", "🔺 BUY"])
    emoji = "🔥" if "SELL" in direction else "📈"

    signal_text = f"""
{direction} SIGNAL! {emoji}

📍 {pair}
⏱ Timeframe: {timeframe}
💰 Amount: ${DEFAULT_AMOUNT}
⏳ Expiration: {DEFAULT_EXPIRATION}s
🕒 {datetime.now().strftime('%H:%M:%S')}
    """.strip()

    # Send to the chat
    await query.edit_message_text(signal_text)

    # TODO: Here you can add real trade execution using Pocket Option SSID + WebSocket library

    # Optional: Auto-delete or follow-up after expiration
    await asyncio.sleep(DEFAULT_EXPIRATION)
    await query.message.reply_text(f"✅ Signal for {pair} expired.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /signal to create new signals.\nOnly admin can use it.")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", send_signal))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
