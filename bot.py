import os
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from groq import Groq

# Ambil Config dari Environment Railway
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
    # Mengambil data emas dari Yahoo Finance
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

def calculate_sma(prices, period=5):
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 2)

async def analyze_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Menentukan aset berdasarkan command (/btc atau /gold)
    command = update.message.text.lower()
    asset = "BTC" if "btc" in command else "GOLD"
    
    await update.message.reply_text(f"⏳ Menganalisa {asset}, tunggu sebentar...")
    
    try:
        if asset == "BTC":
            prices = get_btc_data()
        else:
            prices = get_gold_data()
            
        rsi = calculate_rsi(prices)
        sma = calculate_sma(prices)
        current_price = prices[-1]

        prompt = (
            f"Bertindaklah sebagai analis trading profesional. Berikan analisa untuk {asset}:\n"
            f"Harga Saat Ini: {current_price}\n"
            f"RSI (7 hari): {rsi}\n"
            f"SMA (5 hari): {sma}\n\n"
            "Instruksi: Berikan rekomendasi singkat (BUY, SELL, atau HOLD) beserta alasannya berdasarkan indikator tersebut."
        )

        # UPDATE: Menggunakan model Llama 3.3 yang masih aktif
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        
        analysis = chat_completion.choices[0].message.content
        await update.message.reply_text(f"📊 **HASIL ANALISA {asset}**\n\n{analysis}", parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

if __name__ == '__main__':
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        print("Error: Variabel lingkungan belum lengkap!")
    else:
        # Inisialisasi bot (PTB v20+)
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        
        app.add_handler(CommandHandler("btc", analyze_signal))
        app.add_handler(CommandHandler("gold", analyze_signal))
        
        print("Bot trading sedang berjalan...")
        app.run_polling()
