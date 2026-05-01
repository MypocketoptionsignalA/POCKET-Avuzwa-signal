import asyncio
import logging
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, POCKET_SSID, DEFAULT_AMOUNT, USE_DEMO, TIMEFRAMES
from pocket_api import PocketOptionClient

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

PAIRS = [
    "🇺🇸🇯🇵 USD/JPY OTC",
    "🇬🇧🇺🇸 GBP/USD OTC",
    "🇬🇧🇯🇵 GBP/JPY OTC",
    "🇪🇺🇺🇸 EUR/USD OTC",
    "🇦🇺🇺🇸 AUD/USD OTC"
]

CLEAN_PAIRS = {p: p.split()[-3] + "/" + p.split()[-1] if len(p.split()) > 2 else p for p in PAIRS}  # Simplified

po_api = None

async def init_pocket_api():
    global po_api
    if not POCKET_SSID:
        logger.warning("No POCKET_SSID provided")
        return False
    po_api = PocketOptionClient(POCKET_SSID, is_demo=USE_DEMO)
    return po_api.connect()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return
    await update.message.reply_text("🤖 Bot Ready!\nUse /signal")

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only.")
        return

    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{i}")] for i, pair in enumerate(PAIRS)]
    await update.message.reply_text("📍 **Select Pair**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ Unauthorized.")
        return

    data = query.data

    if data.startswith("pair_"):
        index = int(data.replace("pair_", ""))
        display_pair = PAIRS[index]
        clean_pair = CLEAN_PAIRS.get(display_pair, display_pair.replace("🇺🇸🇯🇵 ", "").replace("🇬🇧🇺🇸 ", "").replace("🇬🇧🇯🇵 ", "").replace("🇪🇺🇺🇸 ", "").replace("🇦🇺🇺🇸 ", ""))

        context.user_data["display_pair"] = display_pair
        context.user_data["clean_pair"] = clean_pair

        # Timeframe buttons - Timeframe = Expiration
        tf_keyboard = [[InlineKeyboardButton(tf, callback_data=f"time_{tf}")] for tf in TIMEFRAMES.keys()]

        await query.edit_message_text(
            f"✅ {display_pair}\n\n⏱ Select Timeframe (Expiration):", 
            reply_markup=InlineKeyboardMarkup(tf_keyboard)
        )

    elif data.startswith("time_"):
        tf = data.replace("time_", "")
        display_pair = context.user_data.get("display_pair")
        clean_pair = context.user_data.get("clean_pair")

        expiration = TIMEFRAMES[tf]          # Timeframe == Expiration time
        direction = random.choice(["call", "put"])

        signal_text = f"""
🔥 {'🔺 BUY' if direction == 'call' else '🔻 SELL'} SIGNAL!
Enter NOW

{display_pair}
⏱ Timeframe: {tf}
💰 Amount: ${DEFAULT_AMOUNT}
⏳ Expiration: {expiration}s
🕒 {datetime.now().strftime('%H:%M:%S')}
        """.strip()

        await query.edit_message_text(signal_text)

        await query.message.reply_text(display_pair)

        # Execute trade with matching timeframe/expiration
        if po_api and po_api.connected:
            success = po_api.buy(clean_pair, DEFAULT_AMOUNT, direction, expiration)
            if success:
                await query.message.reply_text("✅ Trade placed successfully!")
            else:
                await query.message.reply_text("⚠️ Failed to place trade.")
        else:
            await query.message.reply_text("⚠️ API not connected — Signal only.")

        await asyncio.sleep(expiration + 5)
        await query.message.reply_text(f"⏰ {tf} signal expired.")

async def main():
    await init_pocket_api()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 Bot running - Timeframe = Expiration")

    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
