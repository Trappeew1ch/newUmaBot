import asyncio
import logging
from telegram import Update, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode

from config_test import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, UMA_WEBSITE
from database import Database
from groq_client import GroqClient
from keyboards import (
    get_main_keyboard, get_chat_keyboard, get_admin_keyboard,
    get_settings_keyboard, get_about_keyboard, get_broadcast_keyboard
)
from broadcast_scheduler import BroadcastScheduler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class UmaBot:
    def __init__(self):
        self.database = Database()
        self.groq_client = GroqClient()
        self.scheduler = None
        self.user_states = {}  # Для хранения состояний пользователей
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Добавляем пользователя в базу данных
        self.database.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name
        )
        
        welcome_text = f"""
🤖 Добро пожаловать в Uma Bot!

Я — умный ИИ-ассистент, который может:
• Отвечать на ваши вопросы
• Анализировать изображения
• Распознавать голосовые сообщения
• Искать актуальную информацию

Выберите действие:
        """
        
        # Создаем клавиатуру с ссылкой на сайт
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("💬 Новый диалог", callback_data="new_dialog")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="settings")],
            [InlineKeyboardButton("ℹ️ О проекте", callback_data="about")],
            [InlineKeyboardButton("🌐 Открыть сайт", url=UMA_WEBSITE)]
        ]
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    def run(self):
        """Запускает бота"""
        # Создаем приложение
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Инициализируем планировщик
        self.scheduler = BroadcastScheduler(application.bot, self.database)
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", self.start))
        
        # Запускаем планировщик
        asyncio.create_task(self.scheduler.start_scheduler())
        
        # Запускаем бота
        logger.info("Uma Bot запущен!")
        application.run_polling()

if __name__ == "__main__":
    bot = UmaBot()
    bot.run()

