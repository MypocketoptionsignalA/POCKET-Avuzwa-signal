import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID"))   # Your Telegram user ID (only you can trigger signals)

# Pocket Option SSID (extract from browser WebSocket - see instructions below)
POCKET_SSID = os.getenv("POCKET_SSID")

# Default settings
DEFAULT_AMOUNT = 10      # Trade amount in USD
DEFAULT_EXPIRATION = 60  # seconds (1 minute common for OTC)
