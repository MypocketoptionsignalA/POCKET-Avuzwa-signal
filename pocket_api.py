import websocket
import json
import threading
import time

class PocketOptionClient:
    def __init__(self, ssid, is_demo=True):
        self.ssid = ssid
        self.is_demo = is_demo
        self.connected = False
        self.ws = None

    def connect(self):
        try:
            self.ws = websocket.create_connection("wss://api.pocketoption.com/signal/v1")
            
            # Send auth
            auth_message = json.dumps([42, ["auth", {"session": self.ssid if isinstance(self.ssid, str) else json.dumps(self.ssid)}]])
            self.ws.send(auth_message)
            
            self.connected = True
            print("✅ Pocket Option API Connected")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.connected = False
            return False

    def buy(self, asset, amount, action, expiration):
        if not self.connected:
            print("API not connected - Signal only")
            return False

        try:
            trade = {
                "asset": asset,
                "amount": amount,
                "action": action,
                "time": expiration,
                "is_demo": self.is_demo
            }
            message = json.dumps([42, ["trade", trade]])
            self.ws.send(message)
            print(f"✅ Trade sent: {action} {asset}")
            return True
        except:
            print("Trade failed")
            return False
