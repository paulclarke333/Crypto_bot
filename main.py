import os
import requests
import time

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = "8400163494"

portfolio = {
    "BTC": {"id": "bitcoin", "buy_drop": -2, "sell_rise": 2, "buy_amount": 50},
    "XRP": {"id": "ripple", "buy_drop": -3, "sell_rise": 3, "buy_amount": 30},
    "SOL": {"id": "solana", "buy_drop": -3, "sell_rise": 3, "buy_amount": 25},
    "JUP": {"id": "jupiter", "buy_drop": -4, "sell_rise": 4, "buy_amount": 15}
}

last_prices = {}

def get_price(coin_id):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=gbp"
    return requests.get(url).json()[coin_id]["gbp"]

def send_message(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

send_message("🚀 Bot is LIVE 24/7")

while True:
    try:
        for symbol, info in portfolio.items():
            price = get_price(info["id"])

            if symbol in last_prices:
                change = (price - last_prices[symbol]) / last_prices[symbol] * 100

                if change <= info["buy_drop"]:
                    send_message(f"🟢 {symbol} BUY\nBuy ~£{info['buy_amount']}\nMove: {round(change,2)}%")

                elif change >= info["sell_rise"]:
                    send_message(f"🔴 {symbol} SELL\nTake profit\nMove: {round(change,2)}%")

            last_prices[symbol] = price

        time.sleep(300)

    except Exception as e:
        print(e)
        time.sleep(60)
