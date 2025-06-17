
import ccxt
import time
import pandas as pd
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Ladataan API-avaimet .env-tiedostosta
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Binance-yhteys
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True
})

# Telegram-viestitoiminto
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)

# Strategia: RSI + MA
def get_signal(df):
    df["MA"] = df["close"].rolling(window=14).mean()
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))
    if df["RSI"].iloc[-1] < 30 and df["close"].iloc[-1] > df["MA"].iloc[-1]:
        return "BUY"
    elif df["RSI"].iloc[-1] > 70 and df["close"].iloc[-1] < df["MA"].iloc[-1]:
        return "SELL"
    return "HOLD"

# Kaupankäyntiparit
pairs = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
log_file = "trading_log.csv"
initial_balance = 1000.0
balance = initial_balance
loss_streak = 0
max_loss_streak = 3

# Alustetaan loki
if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        f.write("time,pair,signal,price,result,balance\n")

# Pääsilmukka
while True:
    for pair in pairs:
        try:
            ohlcv = exchange.fetch_ohlcv(pair, timeframe="5m", limit=100)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            signal = get_signal(df)
            price = df["close"].iloc[-1]

            result = 0.0
            action = ""

            if signal == "BUY":
                amount = 10 / price
                # Simuloidaan ostoa
                action = f"BUY {pair}"
                result = -10
            elif signal == "SELL":
                # Simuloidaan myyntiä
                action = f"SELL {pair}"
                result = 11  # oletetaan pieni voitto

            balance += result
            if result < 0:
                loss_streak += 1
            else:
                loss_streak = 0

            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_file, "a") as f:
                f.write(f"{now},{pair},{signal},{price:.2f},{result:.2f},{balance:.2f}\n")

            send_telegram(f"{action} @ {price:.2f} | balance: {balance:.2f}")

            if loss_streak >= max_loss_streak:
                send_telegram("🚨 Bottisammutettu tappiorajan vuoksi!")
                exit()

        except Exception as e:
            print("Error:", e)

    time.sleep(300)  # 5 min tauko

