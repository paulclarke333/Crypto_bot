import os
import time
import requests
from collections import deque

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = "8400163494"

CHECK_INTERVAL = 3600  # 1 hour
COOLDOWN_SECONDS = 60 * 60  # 1 hour between same-direction alerts per coin

portfolio = {
    "BTC": {
        "id": "bitcoin",
        "buy_amount": 50,
        "buy_rsi_max": 42,
        "sell_rsi_min": 68,
        "min_change_buy": -0.8,
        "min_change_sell": 1.2,
        "sell_action": "Consider trimming 10-15%",
        "profile": "Core holding",
    },
    "XRP": {
        "id": "ripple",
        "buy_amount": 30,
        "buy_rsi_max": 40,
        "sell_rsi_min": 70,
        "min_change_buy": -1.2,
        "min_change_sell": 1.8,
        "sell_action": "Consider trimming 10-15%",
        "profile": "Event-driven holding",
    },
    "SOL": {
        "id": "solana",
        "buy_amount": 25,
        "buy_rsi_max": 42,
        "sell_rsi_min": 69,
        "min_change_buy": -1.5,
        "min_change_sell": 2.0,
        "sell_action": "Sell 25%",
        "profile": "Growth holding",
    },
    "JUP": {
        "id": "jupiter",
        "buy_amount": 15,
        "buy_rsi_max": 38,
        "sell_rsi_min": 72,
        "min_change_buy": -2.0,
        "min_change_sell": 2.5,
        "sell_action": "Sell 25-33%",
        "profile": "High-risk speculative holding",
    },
}

price_history = {symbol: deque(maxlen=60) for symbol in portfolio}
last_alert_time = {}

def send_message(msg: str) -> None:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=20)

def get_price(coin_id: str) -> float:
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=gbp"
    response = requests.get(url, timeout=20)

    if response.status_code != 200:
        raise Exception(f"API error {response.status_code}")

    data = response.json()
    return float(data[coin_id]["gbp"])

def sma(values, period: int):
    if len(values) < period:
        return None
    return sum(list(values)[-period:]) / period

def calc_rsi(values, period: int = 14):
    vals = list(values)
    if len(vals) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(-period, 0):
        diff = vals[i] - vals[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def trend_label(sma20, sma50):
    if sma20 is None or sma50 is None:
        return "Unknown"
    if sma20 > sma50:
        return "Up"
    if sma20 < sma50:
        return "Down"
    return "Flat"

def in_cooldown(symbol: str, side: str) -> bool:
    key = f"{symbol}_{side}"
    last_time = last_alert_time.get(key)
    if last_time is None:
        return False
    return (time.time() - last_time) < COOLDOWN_SECONDS

def mark_alert(symbol: str, side: str):
    key = f"{symbol}_{side}"
    last_alert_time[key] = time.time()

def build_buy_message(symbol, price, change, rsi, trend, amount, profile):
    return (
        f"🟢 {symbol} BUY SETUP\n"
        f"Price: £{price:.4f}\n"
        f"1h move: {change:.2f}%\n"
        f"Trend: {trend}\n"
        f"RSI: {rsi:.1f}\n"
        f"Action: Buy ~£{amount}\n"
        f"Reason: Pullback in acceptable conditions\n"
        f"Profile: {profile}"
    )

def build_sell_message(symbol, price, change, rsi, trend, action, profile):
    return (
        f"🔴 {symbol} TAKE PROFIT / SELL SETUP\n"
        f"Price: £{price:.4f}\n"
        f"1h move: {change:.2f}%\n"
        f"Trend: {trend}\n"
        f"RSI: {rsi:.1f}\n"
        f"Action: {action}\n"
        f"Reason: Fast move / overheated conditions\n"
        f"Profile: {profile}"
    )

send_message("🚀 Smarter crypto bot is now live")

while True:
    try:
        btc_trend_ok = True

        for symbol, info in portfolio.items():
            time.sleep(5)
            price = get_price(info["id"])
            history = price_history[symbol]
            previous_price = history[-1] if len(history) > 0 else None
            history.append(price)

            sma20 = sma(history, 20)
            sma50 = sma(history, 50)
            rsi = calc_rsi(history, 14)
            trend = trend_label(sma20, sma50)

            if symbol == "BTC" and trend == "Down":
                btc_trend_ok = False

            if previous_price is None or rsi is None or sma20 is None:
                continue

            change = ((price - previous_price) / previous_price) * 100

            buy_ok = (
                trend in ["Up", "Flat"]
                and rsi <= info["buy_rsi_max"]
                and change <= info["min_change_buy"]
            )

            sell_ok = (
                rsi >= info["sell_rsi_min"]
                and change >= info["min_change_sell"]
            )

            if symbol in ["XRP", "SOL", "JUP"] and not btc_trend_ok:
                buy_ok = False

            if buy_ok and not in_cooldown(symbol, "buy"):
                send_message(
                    build_buy_message(
                        symbol=symbol,
                        price=price,
                        change=change,
                        rsi=rsi,
                        trend=trend,
                        amount=info["buy_amount"],
                        profile=info["profile"],
                    )
                )
                mark_alert(symbol, "buy")

            elif sell_ok and not in_cooldown(symbol, "sell"):
                send_message(
                    build_sell_message(
                        symbol=symbol,
                        price=price,
                        change=change,
                        rsi=rsi,
                        trend=trend,
                        action=info["sell_action"],
                        profile=info["profile"],
                    )
                )
                mark_alert(symbol, "sell")

        time.sleep(CHECK_INTERVAL)

    except Exception as e:
        send_message(f"⚠️ Bot error: {str(e)}")
        time.sleep(900)
