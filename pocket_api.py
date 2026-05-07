import websocket
import json

class PocketOptionClient:
    def __init__(self, ssid, is_demo=True):
        self.ssid = ssid.strip() if isinstance(ssid, str) else ssid
        self.is_demo = is_demo
        self.connected = False
        self.ws = None

    def connect(self):
        try:
            self.ws = websocket.create_connection("wss://api.pocketoption.com/signal/v1", timeout=10)
            
            auth_data = {"session": self.ssid} if isinstance(self.ssid, str) else self.ssid
            message = json.dumps([42, ["auth", auth_data]])
            self.ws.send(message)
            
            self.connected = True
            print("✅ PocketOption Connected")
            return True
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            self.connected = False
            return False

    def buy(self, asset, amount, action, expiration):
        if not self.connected or not self.ws:
            print("⚠️ API not connected")
            return False

        try:
            trade = {
                "asset": asset,
                "amount": int(amount),
                "action": action,
                "time": int(expiration),
                "is_demo": self.is_demo
            }
            message = json.dumps([42, ["trade", trade]])
            self.ws.send(message)
            print(f"✅ Trade sent: {action} {asset}")
            return True
        except Exception as e:
            print(f"Trade failed: {e}")
            return False
