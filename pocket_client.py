# pocket_client.py
import asyncio
import json
import websocket
import threading
from config import TIMEFRAME

class PocketClient:
    def __init__(self, ssid):
        self.ssid = ssid
        self.ws = None
        self.candles = {}
        self.running = False

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
            # Handle candle data here (simplified)
            if isinstance(data, list) and len(data) > 1:
                if data[0] == "candles":
                    asset = data[1].get("asset")
                    if asset:
                        self.candles[asset] = data[1].get("candles", [])
        except:
            pass

    def on_open(self, ws):
        print("✅ Connected to Pocket Option WebSocket")
        # Subscribe to candles
        for asset in list(active_assets):
            subscribe_msg = json.dumps(["subscribe", "candles", {"asset": asset, "period": TIMEFRAME}])
            ws.send(subscribe_msg)

    def connect(self):
        self.running = True
        url = "wss://ws.binaryws.com/websockets/v3?app_id=...&l=EN"  # Pocket uses similar
        
        self.ws = websocket.WebSocketApp(
            "wss://api.pocketoption.com/signal/v1",  # Adjust if needed
            on_open=self.on_open,
            on_message=self.on_message
        )
        
        threading.Thread(target=self.ws.run_forever, daemon=True).start()
        asyncio.sleep(3)  # Wait for connection

    async def get_candles(self, asset, count=100):
        # Fallback to stored candles
        return self.candles.get(asset, [])
