import asyncio
import logging
import random
from datetime import datetime
import pytz
 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
 
from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, POCKET_SSID, DEFAULT_AMOUNT, USE_DEMO, TIMEFRAMES
from pocket_api import PocketOptionClient
 
logging.basicConfig(level=logging.INFO)
 
SAST = pytz.timezone('Africa/Johannesburg')
 
PAIRS = [
    "🇺🇸🇯🇵 USD/JPY OTC",
    "🇬🇧🇺🇸 GBP/USD OTC",
    "🇬🇧🇯🇵 GBP/JPY OTC",
    "🇪🇺🇺🇸 EUR/USD OTC",
    "🇦🇺🇺🇸 AUD/USD OTC",
    "🇪🇺🇯🇵 EUR/JPY OTC",
    "🇦🇺🇯🇵 AUD/JPY OTC",
    "🇳🇿🇺🇸 NZD/USD OTC",
    "🇺🇸🇨🇭 USD/CHF OTC",
    "🇪🇺🇬🇧 EUR/GBP OTC",
    "🇬🇧🇦🇺 GBP/AUD OTC",
    "🇪🇺🇦🇺 EUR/AUD OTC",
    "🇦🇺🇨🇭 AUD/CHF OTC",
    "🇨🇦🇯🇵 CAD/JPY OTC",
    "🇬🇧🇨🇭 GBP/CHF OTC",
    "🇪🇺🇨🇭 EUR/CHF OTC",
    "🇳🇿🇯🇵 NZD/JPY OTC",
    "🇺🇸🇨🇦 USD/CAD OTC"
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
        await update.message.reply_text("Unauthorized")
        return
    await update.message.reply_text("Bot Ready! /signal")
 
async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Admin only")
        return
 
    # Square keyboard buttons (2 columns)
    keyboard = [[PAIRS[i], PAIRS[i+1]] if i+1 < len(PAIRS) else [PAIRS[i]] for i in range(0, len(PAIRS), 2)]
    await update.message.reply_text("Select Pair", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
 
async def handle_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    selected = update.message.text
    if selected in PAIRS:
        display_pair = selected
        clean_pair = CLEAN_PAIRS[display_pair]
        
        context.user_data["pair"] = clean_pair
        context.user_data["display"] = display_pair
        
        tf_keyboard = [[InlineKeyboardButton(tf, callback_data=f"time_{tf}")] for tf in TIMEFRAMES.keys()]
        await update.message.reply_text(f"{display_pair}\nChoose Timeframe", reply_markup=InlineKeyboardMarkup(tf_keyboard))
 
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
 
    if query.from_user.id != ADMIN_USER_ID:
        return
 
    data = query.data
    if data.startswith("time_"):
        tf = data.replace("time_", "")
        display_pair = context.user_data.get("display")
        clean_pair = context.user_data.get("pair")
 
        direction = random.choice(["call", "put"])
        signal = f"{'BUY' if direction == 'call' else 'SELL'} SIGNAL! Enter NOW\n\n{display_pair}"
 
        await query.edit_message_text(signal)
 
        if po_api and po_api.connected:
            po_api.buy(clean_pair, DEFAULT_AMOUNT, direction, TIMEFRAMES[tf])
 
        await asyncio.sleep(TIMEFRAMES[tf] + 5)
        await query.message.reply_text("Signal expired.")
 
async def main():
    await init_pocket_api()
 
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
 
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_pair))
    app.add_handler(CallbackQueryHandler(button_handler))
 
    print("Simple Inline Bot Started")
 
    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()
 
if __name__ == "__main__":
    asyncio.run(main())
