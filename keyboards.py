from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from config import UMA_WEBSITE

def get_main_keyboard() -> InlineKeyboardMarkup:
	keyboard = [
		[InlineKeyboardButton(text="💬 Новый диалог", callback_data="new_dialog")],
		[InlineKeyboardButton(text="📜 История", callback_data="history")],
		[InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
		[InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about")],
		[InlineKeyboardButton(text="🌐 Открыть сайт", url=UMA_WEBSITE)],
	]
	return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_chat_keyboard() -> InlineKeyboardMarkup:
	keyboard = [
		[
			InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="regenerate"),
			InlineKeyboardButton(text="📋 В меню", callback_data="main_menu"),
		],
	]
	return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_keyboard() -> InlineKeyboardMarkup:
	keyboard = [
		[InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
		[InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
		[InlineKeyboardButton(text="✏️ Сообщение рассылки", callback_data="admin_message")],
		[InlineKeyboardButton(text="🗓 Планировщик", callback_data="admin_scheduler")],
		[InlineKeyboardButton(text="🚀 Тестовая рассылка", callback_data="admin_send_broadcast")],
		[InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
	]
	return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_uma_website_keyboard() -> InlineKeyboardMarkup:
	keyboard = [
		[InlineKeyboardButton(text="🌐 Открыть сайт", url=UMA_WEBSITE)],
	]
	return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_settings_keyboard() -> InlineKeyboardMarkup:
	keyboard = [
		[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
		[InlineKeyboardButton(text="🗑 Очистить историю", callback_data="clear_history")],
	]
	return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_about_keyboard() -> InlineKeyboardMarkup:
	keyboard = [
		[InlineKeyboardButton(text="🌐 Открыть сайт", url=UMA_WEBSITE)],
		[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")],
	]
	return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_broadcast_keyboard() -> InlineKeyboardMarkup:
	keyboard = [
		[InlineKeyboardButton(text="🌐 Открыть сайт", url=UMA_WEBSITE)],
		[InlineKeyboardButton(text="💬 Начать чат", callback_data="new_dialog")],
	]
	return InlineKeyboardMarkup(inline_keyboard=keyboard)
