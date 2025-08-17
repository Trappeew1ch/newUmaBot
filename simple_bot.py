import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_BOT_TOKEN = "6642636919:AAFSpwTK2WvJN0TPebJy0sAFY9QJD31aBvo"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = """
🤖 Добро пожаловать в Uma Bot!

Я — умный ИИ-ассистент, который может:
• Отвечать на ваши вопросы
• Анализировать изображения
• Распознавать голосовые сообщения
• Искать актуальную информацию

Бот успешно запущен! 🎉
    """
    
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📋 Доступные команды:
/start - Запуск бота
/help - Эта справка

Бот работает! ✅
    """
    
    await update.message.reply_text(help_text)

def main():
    """Запускает бота"""
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    # Запускаем бота
    logger.info("Uma Bot запущен!")
    print("🤖 Uma Bot запущен! Нажмите Ctrl+C для остановки.")
    
    try:
        application.run_polling()
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    main()

