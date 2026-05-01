import json
import asyncio
import logging
from websocket import create_connection, WebSocket

logger = logging.getLogger(__name__)

class PocketOptionClient:
    def __init__(self, ssid: str, is_demo: bool = True):
        self.ssid = ssid.strip()
        self.is_demo = is_demo
        self.ws = None
        self.connected = False

    def connect(self):
        try:
            self.ws = create_connection("wss://api.pocketoption.com/signal/v1")
            # Authenticate
            auth_message = json.dumps(["auth", {"session": self.ssid, "is_demo": self.is_demo}])
            self.ws.send(auth_message)
            
            # Wait for auth response
            response = self.ws.recv()
            logger.info(f"Auth response: {response}")
            
            self.connected = True
            logger.info(f"✅ Connected to Pocket Option | Demo: {self.is_demo}")
            return True, "Connected"
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False, str(e)

    def buy(self, asset: str, amount: int, direction: str, duration: int):
        """direction: 'call' or 'put'"""
        if not self.connected or not self.ws:
            return False

        try:
            trade_message = {
                "asset": asset,
                "amount": amount,
                "action": "call" if direction == "call" else "put",
                "time": duration,
                "is_demo": self.is_demo
            }
            self.ws.send(json.dumps(["trade", trade_message]))
            logger.info(f"Trade sent: {asset} | {direction.upper()} | ${amount} | {duration}s")
            return True
        except Exception as e:
            logger.error(f"Buy error: {e}")
            return False

    def get_balance(self):
        # Simplified - many APIs require a separate balance request
        return "Balance check not implemented in basic client"
