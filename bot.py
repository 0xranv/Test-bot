import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

def get_btc_data():
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=7&interval=daily"
    r = requests.get(url, timeout=10)
    data = r.json()
    prices = [round(p[1], 2) for p in data["prices"]]
    return prices

def get_gold_data():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1d&range=7d"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=10)
    data = r.json()
    closes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
    return [round(p, 2) for p in closes if p]

def calculate_rsi(prices, period=7):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def calculate_sma(prices, period):
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 2)

def analyze_trend(prices):
    if len(prices) < 3:
        return "SIDEWAYS"
    recent = prices[-3:]
    if recent[-1] > recent[0] * 1.005:
        return "BULLISH 📈"
    elif recent[-1] < recent[0] * 0.995:
        return "BEARISH 📉"
    return "SIDEWAYS ➡️"

def get_ai_analysis(asset, prices):
    current = prices[-1]
    prev = prices[-2] if len(prices) > 1 else current
    change = round(((current - prev) / prev) * 100, 2)
    sma5 = calculate_sma(prices, 5)
    rsi = calculate_rsi(prices)
    trend = analyze_trend(prices)

    prompt = f"""
Kamu adalah analis trading profesional. Analisa aset berikut:

Aset: {asset}
Harga sekarang: ${current:,.2f}
Perubahan 24h: {change}%
SMA 5: {sma5}
RSI: {rsi}
Tren: {trend}
Harga 7 hari terakhir: {prices}

Berikan analisa dalam format ini:
1. 📊 SINYAL: (BUY/SELL/HOLD)
2. 🎯 PROBABILITAS: (persentase keyakinan sinyal)
3. 🏹 TARGET: (harga target)
4. 🛡️ STOP LOSS: (level stop loss)
5. 📝 ANALISA: (2-3 kalimat penjelasan)
6. ⚠️ DISCLAIMER: (risiko trading)

Gunakan bahasa Indonesia. Pakai emoji. Jawab singkat dan jelas.
"""

    response = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.3
    )
    return response.choices[0].message.content

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🤖 *Gold & BTC AI Analyst Bot*\n\n"
        "Perintah tersedia:\n"
        "/btc — Analisa Bitcoin\n"
        "/gold — Analisa Gold\n\n"
        "⚠️ Bukan saran investasi ya!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def btc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Menganalisa BTC, tunggu sebentar...")
    try:
        prices = get_btc_data()
        result = get_ai_analysis("Bitcoin BTC/USD", prices)
        header = f"₿ *ANALISA BITCOIN*\n🕐 {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
        await update.message.reply_text(header + result, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal: {str(e)}")

async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Menganalisa Gold, tunggu sebentar...")
    try:
        prices = get_gold_data()
        result = get_ai_analysis("Gold XAU/USD", prices)
        header = f"🥇 *ANALISA GOLD*\n🕐 {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
        await update.message.reply_text(header + result, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Gagal: {str(e)}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("btc", btc))
    app.add_handler(CommandHandler("gold", gold))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
