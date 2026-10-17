import os
# config.py

# --- Telegram Bot ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", 'YOUR_TELEGRAM_CHANNEL_ID')

# --- Google Gemini AI ---
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", 'YOUR_GOOGLE_API_KEY')

# {symbol} и {data} будут автоматически подставлены программой
GEMINI_PROMPT_TEMPLATE = """
Ты — эксперт по техническому анализу криптовалют. 
Тебе предоставлены данные OHLC для {symbol}.
Твоя задача — проанализировать эти данные и предоставить один стоп-лосс и два тейк-профита (TP1 и TP2). Это должен быть среднесрочный прогноз. Желательно чтобы соотношение риск прибыль был 2:1 по первому тейк-профиту

ДАННЫЕ:
{data}

ВАЖНО: Твой ответ должен содержать ТОЛЬКО три строки в следующем формате, без каких-либо других слов, приветствий или объяснений:
Stop-Loss: [число]
Take-Profit-1: [число]
Take-Profit-2: [число]
"""