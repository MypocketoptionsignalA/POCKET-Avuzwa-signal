import os
import asyncio
import logging
import pandas as pd
import pandas_ta as ta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from pocketoptionapi_async import AsyncPocketOptionClient, OrderDirection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (to be set by user)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
POCKET_OPTION_SSID = os.getenv("POCKET_OPTION_SSID")
IS_DEMO = os.getenv("IS_DEMO", "True").lower() == "true"
TRADE_AMOUNT = float(os.getenv("TRADE_AMOUNT", "1.0"))
TRADE_DURATION = int(os.getenv("TRADE_DURATION", "60"))
ASSETS = os.getenv("ASSETS", "EURUSD_otc,GBPUSD_otc").split(",")

# Initialize Telegram Bot
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Initialize Pocket Option Client
po_client = AsyncPocketOptionClient(POCKET_OPTION_SSID, is_demo=IS_DEMO)

# Global state
is_running = False

async def get_signal(asset):
    """
    Simple strategy: RSI + Bollinger Bands
    - CALL: Price below lower BB and RSI < 30
    - PUT: Price above upper BB and RSI > 70
    """
    try:
        candles = await po_client.get_candles_dataframe(asset=asset, timeframe=60)
        if candles.empty:
            return None
        
        # Calculate indicators
        candles.ta.rsi(length=14, append=True)
        candles.ta.bbands(length=20, std=2, append=True)
        
        last_row = candles.iloc[-1]
        rsi = last_row['RSI_14']
        lower_bb = last_row['BBL_20_2.0']
        upper_bb = last_row['BBU_20_2.0']
        close = last_row['close']
        
        if close < lower_bb and rsi < 30:
            return OrderDirection.CALL
        elif close > upper_bb and rsi > 70:
            return OrderDirection.PUT
        
        return None
    except Exception as e:
        logger.error(f"Error getting signal for {asset}: {e}")
        return None

async def trading_loop():
    global is_running
    while is_running:
        for asset in ASSETS:
            signal = await get_signal(asset)
            if signal:
                direction_str = "CALL" if signal == OrderDirection.CALL else "PUT"
                message = f"🚨 Signal for {asset}: {direction_str}\nExecuting trade..."
                await bot.send_message(chat_id=os.getenv("CHAT_ID"), text=message)
                
                try:
                    order = await po_client.place_order(
                        asset=asset, 
                        amount=TRADE_AMOUNT, 
                        direction=signal, 
                        duration=TRADE_DURATION
                    )
                    await bot.send_message(
                        chat_id=os.getenv("CHAT_ID"), 
                        text=f"✅ Trade placed: {order.order_id}\nAmount: {TRADE_AMOUNT}\nDirection: {direction_str}"
                    )
                except Exception as e:
                    await bot.send_message(
                        chat_id=os.getenv("CHAT_ID"), 
                        text=f"❌ Failed to place trade: {e}"
                    )
            
        await asyncio.sleep(60) # Check every minute

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Welcome to Pocket Option Signal Bot!\nUse /run to start trading and /stop to stop.")

@dp.message(Command("run"))
async def run_handler(message: types.Message):
    global is_running
    if not is_running:
        is_running = True
        os.environ["CHAT_ID"] = str(message.chat.id)
        asyncio.create_task(trading_loop())
        await message.answer("Bot started! Monitoring assets...")
    else:
        await message.answer("Bot is already running.")

@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    global is_running
    is_running = False
    await message.answer("Bot stopped.")

async def main():
    await po_client.connect()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
