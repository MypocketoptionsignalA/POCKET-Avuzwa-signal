import asyncio
import logging
import random
from datetime import datetime
import pytz
 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
 
from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, POCKET_SSID, DEFAULT_AMOUNT, USE_DEMO, TIMEFRAMES
from pocket_api import PocketOptionClient
 
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
 
# South African Timezone
SAST = pytz.timezone('Africa/Johannesburg')
 
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
        logger.warning("No POCKET_SSID provided")
        return False
    po_api = PocketOptionClient(POCKET_SSID, is_demo=USE_DEMO)
    return po_api.connect()
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return
    await update.message.reply_text("🤖 Pocket Signals Bot Ready!\nSend /signal")
 
async def signal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only.")
        return
 
    # Big keyboard buttons at bottom (like Aether IQ)
    keyboard = [[pair] for pair in PAIRS]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
 
    await update.message.reply_text(
        "📍 Select a pair from the keyboard below ⬇️", 
        reply_markup=reply_markup
    )
 
async def pair_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user selects a pair from keyboard"""
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    selected_text = update.message.text
    
    # Check if it's a valid pair
    if selected_text in PAIRS:
        display_pair = selected_text
        clean_pair = CLEAN_PAIRS[display_pair]
        
        context.user_data["display_pair"] = display_pair
        context.user_data["clean_pair"] = clean_pair
        
        # Show timeframe buttons (inline buttons)
        tf_keyboard = [[InlineKeyboardButton(f"⏱ {tf}", callback_data=f"time_{tf}")] for tf in TIMEFRAMES.keys()]
        
        await update.message.reply_text(
            f"✅ Selected: **{display_pair}**\n\nChoose Timeframe:", 
            reply_markup=InlineKeyboardMarkup(tf_keyboard),
            parse_mode="Markdown"
        )
 
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
 
    if query.from_user.id != ADMIN_USER_ID:
        await query.edit_message_text("❌ Unauthorized.")
        return
 
    data = query.data
 
    # Only handle timeframe selection now
    if data.startswith("time_"):
        tf = data.replace("time_", "")
        display_pair = context.user_data.get("display_pair")
        clean_pair = context.user_data.get("clean_pair")
 
        expiration = TIMEFRAMES[tf]
        direction = random.choice(["call", "put"])
 
        # South African Time
        now_sast = datetime.now(SAST)
 
        signal_text = f"""
🔥 {'🔺 BUY' if direction == 'call' else '🔻 SELL'} SIGNAL!
Enter NOW
 
{display_pair}
⏱ Timeframe: {tf}
💰 Amount: ${DEFAULT_AMOUNT}
⏳ Expiration: {expiration}s
🕒 {now_sast.strftime('%H:%M:%S')}
        """.strip()
 
        await query.edit_message_text(signal_text)
 
        # Real Trade
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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pair_message_handler))
    application.add_handler(CallbackQueryHandler(button_handler))
 
    print("🚀 Bot running - Pairs on Keyboard + SAST Time")
 
    async with application:
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()
 
if __name__ == "__main__":
    asyncio.run(main())
