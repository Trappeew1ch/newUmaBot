import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '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')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '6642636919:AAFSpwTK2WvJN0TPebJy0sAFY9QJD31aBvo')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '123456789'))  # Временный ID для тестирования

# Groq Models
TEXT_MODEL = "openai/gpt-oss-120b"
MULTIMODAL_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
AUDIO_MODEL = "whisper-large-v3-turbo"

# File size limits
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_IMAGE_PIXELS = 33 * 1024 * 1024  # 33 megapixels
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB for free tier

# Website
UMA_WEBSITE = "https://umaai.site"

# Daily broadcast messages
DAILY_MESSAGES = [
    "💡 А вы знали? На Umaai.site есть не только чат-боты, но и генераторы видео, картинок и речи!",
    "🚀 Попробуйте Video 3 прямо в нашем миниапп! Umaai.site",
    "🎨 Хотите сделать уникальную картинку или видео? Umaai.site — ваш креативный центр!"
]

