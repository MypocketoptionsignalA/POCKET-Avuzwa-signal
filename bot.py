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

PAIRS = ["USD/JPY OTC", "GBP/USD OTC", "GBP/JPY OTC", "EUR/USD OTC", "AUD/USD OTC"]

po_api = None

async def init_pocket_api():
    global po_api
    if not POCKET_SSID:
        logger.warning("POCKET_SSID not found in environment variables")
        return False

    po_api = PocketOptionClient(POCKET_SSID, is_demo=USE_DEMO)
    success = po_api.connect()
    return success

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return
    await update.message.reply_text("🤖 Pocket Signals Bot is Online!\n\nUse /signal to start trading.")

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only.")
        return

    # Pairs Keyboard (exactly like you asked)
    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{pair}")] for pair in PAIRS]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("📍 **Select Pair**", 
                                    reply_markup=reply_markup, 
                                    parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ Unauthorized.")
        return

    data = query.data

    # === PAIR SELECTED → Show Timeframes ===
    if data.startswith("pair_"):
        pair = data.replace("pair_", "")
        context.user_data["selected_pair"] = pair

        tf_keyboard = [[InlineKeyboardButton(f"⏱ {tf}", callback_data=f"time_{tf}")] 
                       for tf in TIMEFRAMES.keys()]

        await query.edit_message_text(
            f"✅ Pair: **{pair}**\n\nSelect Timeframe:", 
            reply_markup=InlineKeyboardMarkup(tf_keyboard),
            parse_mode="Markdown"
        )

    # === TIMEFRAME SELECTED → Send Signal + Real Trade ===
    elif data.startswith("time_"):
        tf = data.replace("time_", "")
        pair = context.user_data.get("selected_pair")

        if not pair:
            await query.edit_message_text("❌ Error: Pair not selected.")
            return

        expiration = TIMEFRAMES[tf]
        direction = random.choice(["call", "put"])   # ← Replace with real strategy later
        signal_emoji = "🔺" if direction == "call" else "🔻"
        fire = "🔥" if direction == "put" else "📈"

        signal_text = f"""
{fire} **{signal_emoji} SIGNAL!**

📍 {pair}
⏱ Timeframe: {tf}
💰 Amount: ${DEFAULT_AMOUNT}
⏳ Expiration: {expiration}s
🕒 {datetime.now().strftime('%H:%M:%S')}
        """.strip()

        await query.edit_message_text(signal_text, parse_mode="Markdown")

        # Real Trade
        if po_api and po_api.connected:
            success = po_api.buy(pair, DEFAULT_AMOUNT, direction, expiration)
            if success:
                await query.message.reply_text("✅ Trade placed successfully!")
            else:
                await query.message.reply_text("⚠️ Failed to place trade.")
        else:
            await query.message.reply_text("⚠️ API not connected — Signal sent only.")

        # Expiration notification
        await asyncio.sleep(expiration + 5)
        await query.message.reply_text(f"⏰ {pair} signal has expired.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start   - Start bot\n"
        "/signal  - Select pair & timeframe\n\n"
        "⚠️ Keep USE_DEMO=True for testing!"
    )

async def main():
    global po_api
    await init_pocket_api()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 Pocket Signals Bot with Real WebSocket is running...")

    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
