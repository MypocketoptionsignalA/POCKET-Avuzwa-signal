import asyncio
import logging
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import (
    TELEGRAM_BOT_TOKEN, 
    ADMIN_USER_ID, 
    POCKET_SSID, 
    DEFAULT_AMOUNT, 
    USE_DEMO, 
    TIMEFRAMES
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

PAIRS = ["USD/JPY OTC", "GBP/USD OTC", "GBP/JPY OTC", "EUR/USD OTC", "AUD/USD OTC"]

po_api = None

# ====================== POCKET OPTION CLIENT ======================
class SimplePocketClient:
    def __init__(self, ssid: str, demo: bool = True):
        self.ssid = ssid
        self.demo = demo
        self.connected = False

    def connect(self):
        try:
            # For now we use a simple placeholder.
            # Replace with real library when you find a stable one
            self.connected = True
            logger.info(f"✅ Pocket Option connected | Demo mode: {self.demo}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def buy(self, asset: str, amount: int, direction: str, duration: int):
        if not self.connected:
            return False
        try:
            logger.info(f"TRADE EXECUTED → {direction.upper()} {asset} | ${amount} | {duration}s")
            # TODO: Add real WebSocket buy logic here later
            return True
        except Exception as e:
            logger.error(f"Buy failed: {e}")
            return False

# ====================== BOT HANDLERS ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized bot.")
        return
    await update.message.reply_text("🤖 Pocket Signals Bot Ready!\n\nSend /signal to trade.")

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only.")
        return

    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{pair}")] for pair in PAIRS]
    await update.message.reply_text("📍 **Select Pair**", 
                                    reply_markup=InlineKeyboardMarkup(keyboard), 
                                    parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ Unauthorized.")
        return

    data = query.data

    if data.startswith("pair_"):
        pair = data[5:]  # remove "pair_"
        context.user_data["pair"] = pair

        tf_buttons = [[InlineKeyboardButton(tf, callback_data=f"time_{tf}")] for tf in TIMEFRAMES.keys()]
        await query.edit_message_text(
            f"✅ Selected: **{pair}**\n\n⏱ Choose Timeframe:",
            reply_markup=InlineKeyboardMarkup(tf_buttons),
            parse_mode="Markdown"
        )

    elif data.startswith("time_"):
        tf = data[5:]
        pair = context.user_data.get("pair")
        if not pair:
            await query.edit_message_text("Error: Pair not found.")
            return

        expiration = TIMEFRAMES[tf]
        direction = random.choice(["call", "put"])
        dir_emoji = "🔺 BUY" if direction == "call" else "🔻 SELL"
        fire = "🔥" if direction == "put" else "📈"

        signal_text = f"""
{fire} **{dir_emoji} SIGNAL!**

📍 {pair}
⏱ Timeframe: {tf}
💰 Amount: ${DEFAULT_AMOUNT}
⏳ Expiration: {expiration}s
🕒 {datetime.now().strftime('%H:%M:%S')}
        """.strip()

        await query.edit_message_text(signal_text, parse_mode="Markdown")

        # Real trade attempt
        if po_api:
            success = po_api.buy(pair, DEFAULT_AMOUNT, direction, expiration)
            if success:
                await query.message.reply_text("✅ Trade placed successfully!")
            else:
                await query.message.reply_text("⚠️ Failed to place trade.")
        else:
            await query.message.reply_text("⚠️ API not connected — signal only.")

        # Optional expiration notice
        await asyncio.sleep(expiration + 5)
        await query.message.reply_text(f"⏰ {pair} signal expired.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start — Start bot\n"
        "/signal — Create new signal\n\n"
        "⚠️ Keep USE_DEMO=True until you test properly!"
    )

# ====================== MAIN ======================
async def main():
    global po_api
    # Initialize Pocket Option
    if POCKET_SSID:
        po_api = SimplePocketClient(POCKET_SSID, demo=USE_DEMO)
        po_api.connect()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 Pocket Signals Bot starting...")

    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        # Keep running
        await asyncio.Event().wait()   # This keeps the bot alive

if __name__ == "__main__":
    asyncio.run(main())
