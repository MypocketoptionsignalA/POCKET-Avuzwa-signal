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

# Pairs with flags - shown as big keyboard buttons
PAIRS = [
    "🇺🇸🇯🇵 USD/JPY OTC",
    "🇬🇧🇺🇸 GBP/USD OTC",
    "🇬🇧🇯🇵 GBP/JPY OTC",
    "🇪🇺🇺🇸 EUR/USD OTC",
    "🇦🇺🇺🇸 AUD/USD OTC"
]

CLEAN_PAIRS = {
    "🇺🇸🇯🇵 USD/JPY OTC": "USD/JPY OTC",
    "🇬🇧🇺🇸 GBP/USD OTC": "GBP/USD OTC",
    "🇬🇧🇯🇵 GBP/JPY OTC": "GBP/JPY OTC",
    "🇪🇺🇺🇸 EUR/USD OTC": "EUR/USD OTC",
    "🇦🇺🇺🇸 AUD/USD OTC": "AUD/USD OTC"
}

po_api = None

async def init_pocket_api():
    global po_api
    if not POCKET_SSID:
        logger.warning("⚠️ No POCKET_SSID provided")
        return False
    
    po_api = PocketOptionClient(POCKET_SSID, is_demo=USE_DEMO)
    success = po_api.connect()
    if success:
        logger.info("✅ Pocket Option Connected Successfully")
    else:
        logger.error("❌ Failed to connect to Pocket Option")
    return success

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized. Admin only.")
        return
    await update.message.reply_text(
        "🤖 Pocket Signals Bot is Online!\n\n"
        "Use /signal to select pair and timeframe."
    )

async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only.")
        return

    # Big Pair Buttons on Keyboard
    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{i}")] for i, pair in enumerate(PAIRS)]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📍 **Select Pair**", 
        reply_markup=reply_markup, 
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ Unauthorized.")
        return

    data = query.data

    # Pair Selected
    if data.startswith("pair_"):
        index = int(data.replace("pair_", ""))
        display_pair = PAIRS[index]
        clean_pair = CLEAN_PAIRS[display_pair]

        context.user_data["display_pair"] = display_pair
        context.user_data["clean_pair"] = clean_pair

        # Show Timeframe Buttons
        tf_keyboard = [[InlineKeyboardButton(f"⏱ {tf}", callback_data=f"time_{tf}")] 
                       for tf in TIMEFRAMES.keys()]

        await query.edit_message_text(
            f"✅ Selected:\n**{display_pair}**\n\nChoose Timeframe:", 
            reply_markup=InlineKeyboardMarkup(tf_keyboard),
            parse_mode="Markdown"
        )

    # Timeframe Selected → Send Signal
    elif data.startswith("time_"):
        tf = data.replace("time_", "")
        display_pair = context.user_data.get("display_pair")
        clean_pair = context.user_data.get("clean_pair")

        if not display_pair:
            await query.edit_message_text("❌ Error: Pair not found.")
            return

        expiration = TIMEFRAMES[tf]
        direction = random.choice(["call", "put"])
        
        # Signal style similar to original bot
        if direction == "call":
            signal_text = f"🔺 BUY SIGNAL!\nEnter NOW 🔥\n\n{display_pair}"
        else:
            signal_text = f"🔻 SELL SIGNAL!\nEnter NOW 🔥\n\n{display_pair}"

        await query.edit_message_text(signal_text)

        # Send pair in separate bubble
        await query.message.reply_text(display_pair)

        # Execute Real Trade
        if po_api and po_api.connected:
            success = po_api.buy(clean_pair, DEFAULT_AMOUNT, direction, expiration)
            if success:
                await query.message.reply_text("✅ Trade placed successfully!")
            else:
                await query.message.reply_text("⚠️ Failed to place trade.")
        else:
            await query.message.reply_text("⚠️ API not connected — Signal sent only.")

        # Expiration notice
        await asyncio.sleep(expiration + 5)
        await query.message.reply_text("⏰ Signal has expired.")

async def main():
    await init_pocket_api()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", signal_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("🚀 Pocket Signals Bot Started - Pair Keyboard Active")

    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
