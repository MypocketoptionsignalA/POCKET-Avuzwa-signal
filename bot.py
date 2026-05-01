import asyncio
import logging
import random
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, POCKET_SSID, DEFAULT_AMOUNT, USE_DEMO, TIMEFRAMES

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

PAIRS = ["USD/JPY OTC", "GBP/USD OTC", "GBP/JPY OTC", "EUR/USD OTC", "AUD/USD OTC"]

# Global API
po_api = None

async def init_pocket_api():
    global po_api
    if not POCKET_SSID:
        logger.warning("No POCKET_SSID provided.")
        return False

    try:
        from pocketoptionapi.stable_api import PocketOption
        po_api = PocketOption(POCKET_SSID)
        connected, msg = po_api.connect()

        if connected:
            balance_type = "PRACTICE" if USE_DEMO else "REAL"
            po_api.change_balance(balance_type)
            balance = po_api.get_balance()
            logger.info(f"✅ Pocket Option Connected | Mode: {balance_type} | Balance: ${balance}")
            return True
        else:
            logger.error(f"Connection failed: {msg}")
            return False
    except Exception as e:
        logger.error(f"Pocket Option API Error: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ This bot is for admin only.")
        return
    await update.message.reply_text("🤖 Pocket Signals Bot Ready!\n\nUse /signal to create a new signal.")

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only.")
        return

    # First keyboard: Pairs
    keyboard = []
    for pair in PAIRS:
        keyboard.append([InlineKeyboardButton(pair, callback_data=f"pair_{pair}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📍 Select Pair:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id != ADMIN_USER_ID:
        await query.edit_message_text("❌ Unauthorized.")
        return

    data = query.data

    # Step 1: User selected a pair → show timeframes
    if data.startswith("pair_"):
        pair = data.replace("pair_", "")
        context.user_data["selected_pair"] = pair

        # Timeframe keyboard
        keyboard = []
        for tf in TIMEFRAMES.keys():
            keyboard.append([InlineKeyboardButton(f"⏱ {tf}", callback_data=f"time_{tf}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Selected: **{pair}**\n\nChoose Timeframe:", 
                                      reply_markup=reply_markup, parse_mode="Markdown")

    # Step 2: User selected timeframe → send signal + place real trade
    elif data.startswith("time_"):
        tf = data.replace("time_", "")
        pair = context.user_data.get("selected_pair")

        if not pair:
            await query.edit_message_text("❌ Error: Pair not found.")
            return

        expiration = TIMEFRAMES[tf]
        direction = random.choice(["call", "put"])  # Replace with your strategy later
        dir_text = "🔺 BUY (CALL)" if direction == "call" else "🔻 SELL (PUT)"
        emoji = "📈" if direction == "call" else "🔥"

        signal_text = f"""
{emoji} **{dir_text} SIGNAL!**

📍 {pair}
⏱ Timeframe: {tf}
💰 Amount: ${DEFAULT_AMOUNT}
⏳ Expiration: {expiration}s
🕒 {datetime.now().strftime('%H:%M:%S')}
        """.strip()

        await query.edit_message_text(signal_text, parse_mode="Markdown")

        # === REAL TRADE ===
        if po_api:
            try:
                success = po_api.buy(
                    asset=pair,
                    amount=DEFAULT_AMOUNT,
                    direction=direction,
                    duration=expiration
                )
                if success:
                    await query.message.reply_text("✅ Trade executed successfully on Pocket Option!")
                else:
                    await query.message.reply_text("⚠️ Trade placement failed.")
            except Exception as e:
                logger.error(f"Trade error: {e}")
                await query.message.reply_text(f"⚠️ Trade error: {str(e)[:150]}")
        else:
            await query.message.reply_text("⚠️ API not connected — Signal only (no real trade).")

        # Optional: Notify when signal expires
        await asyncio.sleep(expiration + 3)
        await query.message.reply_text(f"⏰ {pair} {tf} signal has expired.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Commands:\n"
        "/start - Start the bot\n"
        "/signal - Create new signal (Pair → Timeframe)\n\n"
        "⚠️ Test with USE_DEMO=True first!"
    )

async def main():
    await init_pocket_api()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 Pocket Signals Bot is running...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
