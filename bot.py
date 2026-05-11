import asyncio
import logging
import MetaTrader5 as mt5
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, MT5_LOGIN, MT5_PASSWORD, MT5_SERVER

logging.basicConfig(level=logging.INFO)

# Connect to MT5
def connect_mt5():
    if not mt5.initialize(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        print("MT5 Connection Failed")
        return False
    print("✅ Connected to MetaTrader 5")
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Unauthorized")
        return
    await update.message.reply_text("🤖 MT5 Bot Ready!\nUse /signal")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Admin only")
        return

    keyboard = [
        [InlineKeyboardButton("EURUSD", callback_data="EURUSD")],
        [InlineKeyboardButton("GBPUSD", callback_data="GBPUSD")],
        [InlineKeyboardButton("XAUUSD", callback_data="XAUUSD")],
        [InlineKeyboardButton("USDJPY", callback_data="USDJPY")],
    ]

    await update.message.reply_text("Select Pair:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        return

    symbol = query.data

    # Simple Strategy
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 100)
    if rates is None:
        await query.edit_message_text("Failed to get data")
        return

    closes = [rate[4] for rate in rates]
    ema9 = sum(closes[-9:]) / 9
    ema21 = sum(closes[-21:]) / 21

    direction = "BUY" if ema9 > ema21 else "SELL"

    signal_text = f"🚀 **{direction} SIGNAL** 🚀\n\n"
    signal_text += f"Pair: {symbol}\n"
    signal_text += f"Time: {datetime.now().strftime('%H:%M:%S')}"

    await query.edit_message_text(signal_text)

async def main():
    if not connect_mt5():
        print("MT5 Connection Failed")
        return

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("MT5 Bot Started on Railway")

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
