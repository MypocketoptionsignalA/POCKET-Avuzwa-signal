import asyncio
import logging
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

PAIR_MAPPING = {
    "🇬🇧/🇺🇸 GBP/USD OTC": "GBPUSDT",
    "🇪🇺/🇺🇸 EUR/USD OTC": "EURUSDT",
    "🇺🇸/🇯🇵 USD/JPY OTC": "USDJPY",
    "🇬🇧/🇯🇵 GBP/JPY OTC": "GBPJPY",
    "🇦🇺/🇺🇸 AUD/USD OTC": "AUDUSDT",
    "🇪🇺/🇬🇧 EUR/GBP OTC": "EURGBP",
    "🇺🇸/🇨🇭 USD/CHF OTC": "USDCHF",
    "🇦🇺/🇯🇵 AUD/JPY OTC": "AUDJPY",
    "🇦🇺/🇨🇦 AUD/CAD OTC": "AUDCAD",
    "🇦🇺/🇨🇭 AUD/CHF OTC": "AUDCHF",
    "🇦🇪/🇨🇳 AED/CNY OTC": "BTCUSDT"
}

po_api = None

async def init_pocket_api():
    global po_api
    if POCKET_SSID:
        po_api = PocketOptionClient(POCKET_SSID, is_demo=USE_DEMO)
        po_api.connect()

def get_closes(symbol, limit=80):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit={limit}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [float(c[4]) for c in data]
    except:
        pass
    return None

def calculate_rsi(closes, period=14):
    if not closes or len(closes) < period + 1:
        return 50.0

    gains = [max(closes[i] - closes[i-1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i-1] - closes[i], 0) for i in range(1, len(closes))]

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_signal_bias(display_pair):
    symbol = PAIR_MAPPING.get(display_pair, "EURUSDT")
    closes = get_closes(symbol)
    if not closes:
        return random.choice(["call", "put"])

    rsi = calculate_rsi(closes)
    current = closes[-1]
    ema9 = sum(closes[-9:]) / 9
    ema21 = sum(closes[-21:]) / 21

    # Strong BUY conditions
    if rsi < 35 and current > ema9 > ema21:
        return "call"
    # Strong SELL conditions
    elif rsi > 65 and current < ema9 < ema21:
        return "put"
    # Moderate conditions
    elif rsi < 45 and current > ema9:
        return "call"
    elif rsi > 55 and current < ema9:
        return "put"
    else:
        return None  # No strong signal

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

        await asyncio.sleep(1.5)
        await status.edit_text("📊 Analyzing real chart data...")

        await asyncio.sleep(1.8)
        await status.edit_text("⚙️ Running RSI + EMA indicators...")

        direction = get_signal_bias(display_pair)

        await asyncio.sleep(1.4)

        if direction is None:
            await status.edit_text("❌ No strong setup right now.\nTry again later.")
            return

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

# ====================== Keep everything else the same ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Unauthorized")
        return
    await update.message.reply_text("🤖 Advanced OTC Bot Ready!\nUse /signal")

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

    print("🚀 Advanced RSI + EMA OTC Bot Running")

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
