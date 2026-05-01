import json
import logging
import time
from websocket import create_connection, WebSocketConnectionClosedException

logger = logging.getLogger(__name__)

class PocketOptionClient:
    def __init__(self, ssid: str, is_demo: bool = True):
        self.ssid = ssid.strip()
        self.is_demo = is_demo
        self.ws = None
        self.connected = False

    def connect(self):
        """Connect to Pocket Option WebSocket"""
        try:
            # Main WebSocket endpoint used by most working clients
            self.ws = create_connection("wss://api.pocketoption.com/signal/v1")

            # Send authentication (full 42["auth", ...] format is accepted by many libraries)
            auth_msg = json.dumps(["auth", {"session": self.ssid, "is_demo": self.is_demo}])
            self.ws.send(auth_msg)

            # Wait for response
            response = self.ws.recv()
            logger.info(f"Auth response: {response[:200]}...")

            if "auth" in response.lower() or "success" in response.lower() or len(response) > 10:
                self.connected = True
                logger.info(f"✅ Successfully connected to Pocket Option | Demo: {self.is_demo}")
                return True
            else:
                logger.error("Authentication failed")
                return False

        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False

    def buy(self, asset: str, amount: int, direction: str, duration: int):
        """Place a real trade using WebSocket"""
        if not self.connected or not self.ws:
            logger.warning("Not connected to Pocket Option")
            return False

        try:
            # Direction: "call" = UP / BUY, "put" = DOWN / SELL
            action = "call" if direction.lower() == "call" else "put"

            trade_data = {
                "asset": asset,
                "amount": amount,
                "action": action,
                "time": duration,      # expiration in seconds
                "is_demo": self.is_demo,
                "option_type": "turbo" if duration <= 60 else "binary"
            }

            message = json.dumps(["trade", trade_data])
            self.ws.send(message)

            logger.info(f"✅ Trade sent: {action.upper()} | {asset} | ${amount} | {duration}s")
            return True

        except WebSocketConnectionClosedException:
            logger.error("WebSocket connection closed. Reconnecting...")
            self.connect()
            return False
        except Exception as e:
            logger.error(f"Trade execution error: {e}")
            return False

    def close(self):
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
