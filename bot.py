import os
import ccxt
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

# Gunakan Bybit untuk data real-time tanpa blokir IP
exchange = ccxt.bybit()

# Memori diskusi sederhana (disimpan di RAM)
user_chats = {}

def get_live_market_data(symbol):
    # Ambil harga real-time (0 delay)
    ticker = exchange.fetch_ticker(symbol)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=10)
    closes = [x[4] for x in ohlcv]
    return ticker['last'], closes

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_text = update.message.text
    
    # Inisialisasi memori chat jika belum ada
    if user_id not in user_chats:
        user_chats[user_id] = []

    # Deteksi aset (Default ke BTC jika tidak sebut gold)
    symbol = 'XAUT/USDT' if 'gold' in user_text.lower() or 'xaut' in user_text.lower() else 'BTC/USDT'
    
    try:
        current_price, prices = get_live_market_data(symbol)
        
        # Tambahkan instruksi scalping dan memori ke prompt
        history = "\n".join(user_chats[user_id][-5:]) # Ambil 5 chat terakhir
        
        prompt = (
            f"Kamu adalah Partner Trading Live Pro sangat berpengalam selama 20 tahun, memahami kondisi market global. Diskusikan aset {symbol}.\n"
            f"Harga SAAT INI (Real-time): {current_price}\n"
            f"Data 15m terakhir: {prices}\n"
            f"Diskusi sebelumnya:\n{history}\n"
            f"Pertanyaan user: {user_text}\n"
            "Berikan analisa teknikal high conviction dan jawab pertanyaannya secara natural."
        )

        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        
        response = chat_completion.choices[0].message.content
        
        # Simpan ke memori
        user_chats[user_id].append(f"User: {user_text}")
        user_chats[user_id].append(f"AI: {response}")
        
        await update.message.reply_text(response, parse_mode='Markdown')

    except Exception as e:
        await update.message.reply_text(f"💢 Lagi lag API-nya: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Biar bisa diskusi tanpa command /, pakai MessageHandler
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    # Tetap sediakan command buat trigger awal
    app.add_handler(CommandHandler("btc", handle_message))
    app.add_handler(CommandHandler("gold", handle_message))
    
    print("Bot Live Discussion Jalan...")
    app.run_polling()
