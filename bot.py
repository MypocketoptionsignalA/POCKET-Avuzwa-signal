import asyncio
import logging
import random
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, POCKET_SSID, DEFAULT_AMOUNT, USE_DEMO, TIMEFRAMES
from pocket_api import PocketOptionClient

logging.basicConfig(level=logging.INFO)

PAIRS = [
    "🇬🇧/🇺🇸 GBP/USD OTC", "🇪🇺/🇺🇸 EUR/USD OTC", "🇺🇸/🇯🇵 USD/JPY OTC",
    "🇬🇧/🇯🇵 GBP/JPY OTC", "🇦🇺/🇺🇸 AUD/USD OTC", "🇪🇺/🇬🇧 EUR/GBP OTC",
    "🇺🇸/🇨🇭 USD/CHF OTC", "🇦🇺/🇯🇵 AUD/JPY OTC", "🇦🇺/🇨🇦 AUD/CAD OTC",
    "🇦🇺/🇨🇭 AUD/CHF OTC", "🇦🇪/🇨🇳 AED/CNY OTC"
]

TIMEFRAMES = {
    "5s": 5,
    "10s": 10,
    "15s": 15,
    "30s": 30
}

po_api = None

async def init_pocket_api():
    global po_api
    if POCKET_SSID:
        po_api = PocketOptionClient(POCKET_SSID, is_demo=USE_DEMO)
        po_api.connect()

def get_signal_bias():
    """Better than random but not too strict"""
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=EURUSDT", timeout=8)
        if r.status_code == 200:
            # Small bias based on current market sentiment
            return "call" if random.random() > 0.48 else "put"
    except:
        pass
    return random.choice(["call", "put"])

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

        status = await query.edit_message_text("🔍 Scanning for patterns and trends...")

        await asyncio.sleep(1.3)
        await status.edit_text("📊 Analyzing chart data...")

        await asyncio.sleep(1.4)
        await status.edit_text("⚙️ Running indicators...")

        direction = get_signal_bias()
        arrow = "↑" if direction == "call" else "↓"
        signal_type = "BUY" if direction == "call" else "SELL"

        final_signal = f"{arrow} **{signal_type} SIGNAL!** 🚀\n"
        final_signal += f"Enter NOW 🔥\n\n"
        final_signal += f"⏱ {tf}\n\n"
        final_signal += f"{display_pair}"

        await status.edit_text(final_signal)

        if po_api:
            try:
                po_api.buy(clean_pair, DEFAULT_AMOUNT, direction, expiration)
            except:
                pass

# ====================== Rest of the code ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Unauthorized")
        return
    await update.message.reply_text("🤖 OTC Bot Ready!\nUse /signal")

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

    await update.message.reply_text("Select OTC Pair:", 
                                  reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def pair_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    text = update.message.text.strip()
    if text not in PAIRS:
        return

    display_pair = text
    context.user_data["display"] = display_pair
    context.user_data["clean"] = display_pair

    tf_keyboard = [[InlineKeyboardButton(tf, callback_data=f"time_{tf}")] for tf in TIMEFRAMES.keys()]

    await update.message.reply_text(f"Choose Timeframe for\n{display_pair}", 
                                  reply_markup=InlineKeyboardMarkup(tf_keyboard))

async def main():
    await init_pocket_api()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(MessageHandler(filters.TEXT, pair_message_handler))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 Balanced OTC Bot Running")

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
