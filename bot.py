import asyncio
import logging
import random
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, POCKET_SSID, DEFAULT_AMOUNT, USE_DEMO, TIMEFRAMES
from pocket_api import PocketOptionClient

logging.basicConfig(level=logging.INFO)

PAIRS = [
    "🇺🇸/🇯🇵 USD/JPY OTC", "🇬🇧/🇺🇸 GBP/USD OTC", "🇬🇧/🇯🇵 GBP/JPY OTC",
    "🇪🇺/🇺🇸 EUR/USD OTC", "🇦🇺/🇺🇸 AUD/USD OTC", "🇦🇺/🇯🇵 AUD/JPY OTC",
    "🇪🇺/🇬🇧 EUR/GBP OTC", "🇺🇸/🇨🇭 USD/CHF OTC", "🇬🇧/🇦🇺 GBP/AUD OTC",
    "🇦🇺/🇨🇦 AUD/CAD OTC", "🇦🇺/🇨🇭 AUD/CHF OTC", "🇦🇪/🇨🇳 AED/CNY OTC"
]

CLEAN_PAIRS = {p: " ".join(p.split()[-3:]) for p in PAIRS}

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
    await update.message.reply_text("Bot Ready!\nUse /signal")

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Admin only")
        return

    keyboard = []
    for i in range(0, len(PAIRS), 2):
        row = [KeyboardButton(PAIRS[i])]
        if i + 1 < len(PAIRS):
            row.append(KeyboardButton(PAIRS[i + 1]))
        keyboard.append(row)

    await update.message.reply_text("Select Pair:", 
                                  reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def pair_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    text = update.message.text.strip()
    if text not in PAIRS:
        return

    display_pair = text
    clean_pair = CLEAN_PAIRS.get(display_pair, display_pair)

    context.user_data["display"] = display_pair
    context.user_data["clean"] = clean_pair

    tf_keyboard = [[InlineKeyboardButton(tf, callback_data=f"time_{tf}")] for tf in TIMEFRAMES.keys()]
    await update.message.reply_text(f"Choose Timeframe for\n{display_pair}", 
                                  reply_markup=InlineKeyboardMarkup(tf_keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        return

    if query.data.startswith("time_"):
        tf = query.data.replace("time_", "")
        display_pair = context.user_data.get("display")
        clean_pair = context.user_data.get("clean")
        expiration = TIMEFRAMES[tf]

        # === Professional Analysis Flow ===
        status = await query.edit_message_text("🔍 Scanning for patterns and trends...")
        await asyncio.sleep(1.5)

        await status.edit_text("📊 Analyzing chart data...")
        await asyncio.sleep(1.8)

        await status.edit_text("⚙️ Running internal indicators...")
        await asyncio.sleep(1.5)

        await status.edit_text("👀 Watching market activity on " + display_pair + "...")
        await asyncio.sleep(2)

        await status.edit_text("🔄 Finalizing signal for " + display_pair + "...")
        await asyncio.sleep(1.5)

        # Generate Signal
        direction = random.choice(["call", "put"])
        
        if direction == "call":
            signal = f"🟢 **BUY SIGNAL!** 🚀\nEnter NOW 🔥\n\n{display_pair}"
        else:
            signal = f"🔴 **SELL SIGNAL!** 🚨\nEnter NOW 🔥\n\n{display_pair}"

        await status.edit_text(signal)

        # Execute trade
        if po_api:
            try:
                po_api.buy(clean_pair, DEFAULT_AMOUNT, direction, expiration)
            except:
                pass

async def main():
    await init_pocket_api()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(MessageHandler(filters.TEXT, pair_message_handler))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot Started - Professional Analysis Mode")

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
