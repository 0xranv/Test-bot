import os
import ccxt  # Library gratis untuk data real-time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from groq import Groq

# Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

# Inisialisasi Exchange (Gratis, tanpa API Key untuk baca harga)
exchange = ccxt.binance()

def get_realtime_prices(symbol):
    # Mengambil data 15 menit terakhir secara real-time
    # Symbol format: 'BTC/USDT' atau 'PAXG/USDT' (untuk Gold)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=20)
    return [x[4] for x in ohlcv] # Mengambil list harga Close

def calculate_rsi(prices, period=7):
    if len(prices) < period + 1: return 50
    gains = [max(prices[i] - prices[i-1], 0) for i in range(1, len(prices))]
    losses = [max(prices[i-1] - prices[i], 0) for i in range(1, len(prices))]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

async def analyze_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    # Otomatis pilih XAUT jika input mengandung kata 'gold'
    if 'gold' in text:
        symbol = 'XAUT/USDT'
    else:
        symbol = 'BTC/USDT'
    
    await update.message.reply_text(f"🚀 Mencari sinyal real-time {symbol}...")
    # ... sisa kode lainnya sama ...


    try:
        prices = get_realtime_prices(symbol)
        current_price = prices[-1]
        prev_price = prices[-2]
        
        # LOGIKA AUTO-SWITCH STRATEGI
        # 1. Cek Volatilitas (Jika harga gerak > 0.4% dalam 15m, kemungkinan ada NEWS)
        price_change = abs(current_price - prev_price) / prev_price
        rsi = calculate_rsi(prices)
        
        if price_change > 0.004:
            strategy_type = "STRATEGI A (Volatility/News Scalping)"
            market_condition = "Ekstrem/Volatil"
            instruction = "Fokus pada Support/Resistance kuat, jangan lawan arus (Trend Following)."
        else:
            strategy_type = "STRATEGI B (Sideways/RSI Scalping)"
            market_condition = "Stabil/Normal"
            instruction = "Fokus pada RSI Overbought/Oversold (Mean Reversion)."

        prompt = (
            f"Kamu adalah AI Scalper Pro. Analisa {symbol} timeframe 15m.\n"
            f"Kondisi Market: {market_condition} ({strategy_type})\n"
            f"Harga Real-time: {current_price}\n"
            f"RSI: {rsi}\n\n"
            f"Tugas: {instruction} Berikan sinyal BUY/SELL/WAIT yang sangat singkat."
        )

        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        
        result = chat_completion.choices[0].message.content
        msg = f"📊 **ANALISA REAL-TIME {symbol}**\n\n💰 Harga: `{current_price}`\n📈 RSI: `{rsi}`\n🛠 Mode: `{strategy_type}`\n\n{result}"
        await update.message.reply_text(msg, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"❌ Gagal ambil data: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("btc", analyze_signal))
    app.add_handler(CommandHandler("gold", analyze_signal))
    print("Bot Scalper Real-time Jalan...")
    app.run_polling()
