import asyncio
import logging
from typing import Optional
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from config import TELEGRAM_BOT_TOKEN, ADMIN_USER_ID, UMA_WEBSITE
from database import Database
from groq_client import GroqClient
from keyboards import (
	get_main_keyboard, get_chat_keyboard, get_admin_keyboard,
	get_settings_keyboard, get_about_keyboard, get_broadcast_keyboard,
)
from broadcast_scheduler import BroadcastScheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Helpers
def build_file_url(token: str, file_path: str) -> str:
	return f"https://api.telegram.org/file/bot{token}/{file_path}"

class UmaBot:
	def __init__(self) -> None:
		self.database = Database()
		self.groq_client = GroqClient()
		self.user_states: dict[int, str] = {}
		self.user_locks: dict[int, asyncio.Lock] = {}  # Блокировки для каждого пользователя
		self.bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
		self.dp = Dispatcher()
		self.scheduler = BroadcastScheduler(self.bot, self.database)
		self._register_handlers()

	def _get_user_lock(self, user_id: int) -> asyncio.Lock:
		"""Получает или создает блокировку для пользователя"""
		if user_id not in self.user_locks:
			self.user_locks[user_id] = asyncio.Lock()
		return self.user_locks[user_id]

	async def _safe_edit_text(self, message, text: str, reply_markup=None):
		"""Безопасное редактирование текста с обработкой ошибок"""
		try:
			await message.edit_text(text, reply_markup=reply_markup)
		except Exception as e:
			logger.warning(f"Не удалось отредактировать сообщение: {e}")
			# Если содержимое не изменилось, удаляем старое сообщение и отправляем новое
			if "message is not modified" in str(e):
				try:
					await message.delete()
					await message.answer(text, reply_markup=reply_markup)
				except Exception as e2:
					logger.error(f"Не удалось удалить/отправить сообщение: {e2}")
			else:
				# Для других ошибок просто отправляем новое сообщение
				try:
					await message.answer(text, reply_markup=reply_markup)
				except Exception as e2:
					logger.error(f"Не удалось отправить новое сообщение: {e2}")

	async def _split_long_message(self, text: str, max_length: int = 4096) -> list[str]:
		"""Разделяет длинное сообщение на части"""
		if len(text) <= max_length:
			return [text]
		
		messages = []
		current_pos = 0
		
		while current_pos < len(text):
			# Находим место для разрыва (предпочтительно по переносу строки или пробелу)
			end_pos = current_pos + max_length
			
			if end_pos >= len(text):
				messages.append(text[current_pos:])
				break
			
			# Ищем последний перенос строки или пробел в пределах лимита
			last_newline = text.rfind('\n', current_pos, end_pos)
			last_space = text.rfind(' ', current_pos, end_pos)
			
			if last_newline > current_pos:
				split_pos = last_newline + 1
			elif last_space > current_pos:
				split_pos = last_space + 1
			else:
				split_pos = end_pos
			
			messages.append(text[current_pos:split_pos].rstrip())
			current_pos = split_pos
		
		return messages

	async def _process_user_message(self, user_id: int, message_type: str, **kwargs) -> str:
		"""Обрабатывает сообщение пользователя с блокировкой"""
		async with self._get_user_lock(user_id):
			history = self.database.get_conversation_history(user_id)
			
			if message_type == "text":
				text = kwargs.get("text", "")
				use_search = self.groq_client.should_use_browser_search(text)
				return await self.groq_client.process_text_message(
					text=text, 
					conversation_history=history, 
					use_browser_search=use_search
				)
			elif message_type == "image":
				image_url = kwargs.get("image_url", "")
				text = kwargs.get("text", "")
				return await self.groq_client.process_image_message(
					image_url=image_url, 
					text=text, 
					conversation_history=history
				)
			elif message_type == "images":
				image_urls = kwargs.get("image_urls", [])
				text = kwargs.get("text", "")
				return await self.groq_client.process_multiple_images_message(
					image_urls=image_urls, 
					text=text, 
					conversation_history=history
				)
			elif message_type == "audio":
				audio_url = kwargs.get("audio_url", "")
				return await self.groq_client.process_audio_message(
					audio_url=audio_url, 
					conversation_history=history
				)
			else:
				return "Неизвестный тип сообщения"

	async def _handle_media_group_item(self, message: Message, user):
		"""Обрабатывает элемент медиа-группы (альбома)"""
		media_group_id = message.media_group_id
		
		# Инициализируем группу, если её ещё нет
		if media_group_id not in self.media_groups:
			self.media_groups[media_group_id] = {
				'messages': [],
				'user_id': user.id,
				'chat_id': message.chat.id,
				'typing_message': None
			}
			# Отправляем "печатает" сообщение только для первого изображения в группе
			typing_message = await message.answer("Анализирую изображения...")
			self.media_groups[media_group_id]['typing_message'] = typing_message
		
		# Добавляем сообщение в группу
		self.media_groups[media_group_id]['messages'].append(message)
		
		# Ждём 1 секунду, чтобы собрать все изображения из альбома
		await asyncio.sleep(1)
		
		# Проверяем, что мы всё ещё обрабатываем эту группу
		if media_group_id in self.media_groups:
			group_data = self.media_groups[media_group_id]
			messages = group_data['messages']
			typing_message = group_data['typing_message']
			
			# Собираем все URL изображений
			image_urls = []
			captions = []
			
			for msg in messages:
				if msg.photo:
					file_id = msg.photo[-1].file_id
					file = await self.bot.get_file(file_id)
					image_url = build_file_url(TELEGRAM_BOT_TOKEN, file.file_path)
					image_urls.append(image_url)
					if msg.caption:
						captions.append(msg.caption)
			
			# Объединяем все подписи
			combined_caption = " ".join(captions) if captions else ""
			
			# Обрабатываем все изображения как одно сообщение
			response = await self._process_user_message(
				user.id,
				"images",
				image_urls=image_urls,
				text=combined_caption
			)
			
			# Сохраняем в историю
			self.database.add_message_to_conversation(
				user.id,
				{"image_urls": image_urls, "caption": combined_caption, "type": "images", "timestamp": message.date.isoformat()},
				response
			)
			
			# Разделяем длинный ответ на части
			message_parts = await self._split_long_message(response)
			
			# Заменяем "печатает" сообщение первой частью ответа
			await self._safe_edit_text(typing_message, message_parts[0], get_chat_keyboard() if len(message_parts) == 1 else None)
			
			# Отправляем остальные части, если есть
			for i, part in enumerate(message_parts[1:], 1):
				is_last = i == len(message_parts) - 1
				await message.answer(part, reply_markup=get_chat_keyboard() if is_last else None)
			
			# Удаляем группу из памяти
			if media_group_id in self.media_groups:
				del self.media_groups[media_group_id]

	def _register_handlers(self) -> None:
		@self.dp.message(Command("start"))
		async def start_cmd(message: Message):
			user = message.from_user
			if user:
				self.database.add_user(user.id, user.username, user.first_name)
			welcome_text = (
				"🤖 Добро пожаловать в Uma Bot!\n\n"
				"Я — умный ИИ-ассистент.\n\n"
				"• Отвечаю на вопросы\n• Анализирую изображения\n"
				"• Распознаю голос\n• Ищу актуальную информацию\n\n"
				"Выберите действие:"
			)
			await message.answer(welcome_text, reply_markup=get_main_keyboard())

		@self.dp.message(Command("admin"))
		async def admin_cmd(message: Message):
			user = message.from_user
			if user and user.id == ADMIN_USER_ID:
				stats = self.database.get_statistics()
				admin_text = (
					f"🔧 Админ-панель Uma Bot\n\n"
					f"📊 Статистика:\n"
					f"• Пользователей: {stats['total_users']}\n"
					f"• Активных сегодня: {stats['active_today']}\n"
					f"• Сообщений: {stats['total_messages']}\n\n"
					f"Выберите действие:"
				)
				await message.answer(admin_text, reply_markup=get_admin_keyboard())
			else:
				await message.answer("⛔ У вас нет доступа к админ-панели.")

		# Словарь для хранения медиа-групп
		self.media_groups = {}
		
		@self.dp.message(F.photo)
		async def handle_photo(message: Message):
			user = message.from_user
			if not user:
				return
			
			# Проверяем, является ли это частью медиа-группы
			if message.media_group_id:
				# Это часть альбома, обрабатываем через медиа-группу
				await self._handle_media_group_item(message, user)
				return
			
			# Отправляем "печатает" сообщение
			typing_message = await message.answer("Анализирую изображение...")
			
			await self.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
			
			file_id = message.photo[-1].file_id
			file = await self.bot.get_file(file_id)
			image_url = build_file_url(TELEGRAM_BOT_TOKEN, file.file_path)
			caption = message.caption or ""
			
			# Обрабатываем с блокировкой пользователя
			response = await self._process_user_message(
				user.id, 
				"image", 
				image_url=image_url, 
				text=caption
			)
			
			# Сохраняем в историю
			self.database.add_message_to_conversation(
				user.id, 
				{"image_url": image_url, "caption": caption, "type": "image", "timestamp": message.date.isoformat()}, 
				response
			)
			
			# Разделяем длинный ответ на части
			message_parts = await self._split_long_message(response)
			
			# Заменяем "печатает" сообщение первой частью ответа
			await self._safe_edit_text(typing_message, message_parts[0], get_chat_keyboard() if len(message_parts) == 1 else None)
			
			# Отправляем остальные части, если есть
			for i, part in enumerate(message_parts[1:], 1):
				is_last = i == len(message_parts) - 1
				await message.answer(part, reply_markup=get_chat_keyboard() if is_last else None)

		@self.dp.message(F.voice)
		async def handle_voice(message: Message):
			user = message.from_user
			if not user:
				return
			
			# Отправляем "печатает" сообщение
			typing_message = await message.answer("Обрабатываю голосовое сообщение...")
			
			await self.bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)
			
			file_id = message.voice.file_id
			file = await self.bot.get_file(file_id)
			audio_url = build_file_url(TELEGRAM_BOT_TOKEN, file.file_path)
			
			# Обрабатываем с блокировкой пользователя
			response = await self._process_user_message(
				user.id, 
				"audio", 
				audio_url=audio_url
			)
			
			# Сохраняем в историю
			self.database.add_message_to_conversation(
				user.id, 
				{"audio_url": audio_url, "type": "audio", "timestamp": message.date.isoformat()}, 
				response
			)
			
			# Разделяем длинный ответ на части
			message_parts = await self._split_long_message(response)
			
			# Заменяем "печатает" сообщение первой частью ответа
			await self._safe_edit_text(typing_message, message_parts[0], get_chat_keyboard() if len(message_parts) == 1 else None)
			
			# Отправляем остальные части, если есть
			for i, part in enumerate(message_parts[1:], 1):
				is_last = i == len(message_parts) - 1
				await message.answer(part, reply_markup=get_chat_keyboard() if is_last else None)

		@self.dp.message(F.audio)
		async def handle_audio_file(message: Message):
			user = message.from_user
			if not user:
				return
			
			# Отправляем "печатает" сообщение
			typing_message = await message.answer("Обрабатываю аудиофайл...")
			
			await self.bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)
			
			file_id = message.audio.file_id
			file = await self.bot.get_file(file_id)
			audio_url = build_file_url(TELEGRAM_BOT_TOKEN, file.file_path)
			
			# Обрабатываем с блокировкой пользователя
			response = await self._process_user_message(
				user.id, 
				"audio", 
				audio_url=audio_url
			)
			
			# Сохраняем в историю
			self.database.add_message_to_conversation(
				user.id, 
				{"audio_url": audio_url, "type": "audio", "timestamp": message.date.isoformat()}, 
				response
			)
			
			# Разделяем длинный ответ на части
			message_parts = await self._split_long_message(response)
			
			# Заменяем "печатает" сообщение первой частью ответа
			await self._safe_edit_text(typing_message, message_parts[0], get_chat_keyboard() if len(message_parts) == 1 else None)
			
			# Отправляем остальные части, если есть
			for i, part in enumerate(message_parts[1:], 1):
				is_last = i == len(message_parts) - 1
				await message.answer(part, reply_markup=get_chat_keyboard() if is_last else None)

		@self.dp.message(F.document)
		async def handle_document(message: Message):
			doc = message.document
			if not doc:
				return
			
			mime = (doc.mime_type or "").lower()
			
			# Обрабатываем только изображения и аудио как документы
			if mime.startswith("image/"):
				await handle_photo(message)
			elif mime.startswith("audio/"):
				await handle_audio_file(message)
			else:
				await message.answer(
					"Извините, пока не поддерживаю этот тип файлов. Отправьте текст, изображение или голос.", 
					reply_markup=get_chat_keyboard()
				)

		@self.dp.message(F.text)
		async def handle_text(message: Message):
			user = message.from_user
			if not user:
				return
			
			text = message.text or ""
			
			# Проверяем состояние пользователя
			if user.id in self.user_states:
				state = self.user_states[user.id]
				if state == "waiting_broadcast_message":
					# Обработка сообщения для рассылки
					result = await self.scheduler.send_manual_broadcast(text)
					del self.user_states[user.id]
					await message.answer(f"✅ {result}", reply_markup=get_admin_keyboard())
					return
				elif state == "waiting_schedule_time":
					# Обработка времени для планировщика
					try:
						from datetime import datetime
						scheduled_time = datetime.strptime(text, "%d.%m.%Y %H:%M")
						# Здесь можно добавить логику сохранения запланированной рассылки
						del self.user_states[user.id]
						await message.answer(
							f"✅ Рассылка запланирована на {scheduled_time.strftime('%d.%m.%Y %H:%M')}", 
							reply_markup=get_admin_keyboard()
						)
					except ValueError:
						await message.answer(
							"❌ Неверный формат времени. Используйте DD.MM.YYYY HH:MM\n"
							"Например: 15.08.2025 14:30",
							reply_markup=get_admin_keyboard()
						)
					return
			
			# Отправляем "печатает" сообщение
			typing_message = await message.answer("Уже пишу...")
			
			# Обычная обработка текста с блокировкой пользователя
			await self.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
			
			response = await self._process_user_message(
				user.id, 
				"text", 
				text=text
			)
			
			# Сохраняем в историю
			self.database.add_message_to_conversation(
				user.id, 
				{"text": text, "type": "text", "timestamp": message.date.isoformat()}, 
				response
			)
			
			# Разделяем длинный ответ на части
			message_parts = await self._split_long_message(response)
			
			# Заменяем "печатает" сообщение первой частью ответа
			await self._safe_edit_text(typing_message, message_parts[0], get_chat_keyboard() if len(message_parts) == 1 else None)
			
			# Отправляем остальные части, если есть
			for i, part in enumerate(message_parts[1:], 1):
				is_last = i == len(message_parts) - 1
				await message.answer(part, reply_markup=get_chat_keyboard() if is_last else None)

		@self.dp.callback_query()
		async def callbacks(query: CallbackQuery):
			user = query.from_user
			data = query.data or ""
			
			if not user:
				return

			try:
				# Сначала отвечаем на callback, чтобы избежать timeout
				await query.answer()
				
				if data == "new_dialog":
					self.database.clear_conversation(user.id)
					await self._safe_edit_text(query.message, "💬 Новый диалог начат! Отправьте сообщение.", get_chat_keyboard())
				elif data == "settings":
					await self._safe_edit_text(query.message, "⚙️ Настройки\n\nЗдесь вы можете управлять настройками бота.", get_settings_keyboard())
				elif data == "about":
					about_text = (
						"ℹ️ О проекте Uma Bot\n\n"
						"Uma Bot — умный ИИ-ассистент.\n\n"
						"• 💬 Диалоги\n• 🖼️ Анализ изображений\n• 🎤 Речь\n• 🔍 Поиск\n\n"
						"🌐 Подробнее на сайте:"
					)
					await self._safe_edit_text(query.message, about_text, get_about_keyboard())
				elif data == "main_menu":
					await self._safe_edit_text(query.message, "🤖 Главное меню Uma Bot\n\nВыберите действие:", get_main_keyboard())
				elif data == "clear_history":
					self.database.clear_conversation(user.id)
					await self._safe_edit_text(query.message, "🗑 История диалога очищена!", get_main_keyboard())
				elif data == "regenerate":
					history = self.database.get_conversation_history(user.id, limit=1)
					if history:
						last_message = history[-1]["message"]
						if last_message.get("type") == "text":
							resp = await self._process_user_message(
								user.id, 
								"text", 
								text=last_message["text"]
							)
							self.database.add_message_to_conversation(user.id, last_message, resp)
							await self._safe_edit_text(query.message, resp, get_chat_keyboard())
						else:
							await query.message.answer("Перегенерация доступна только для текста")
					else:
						await query.message.answer("Нет сообщений для перегенерации")
				elif data == "history":
					h = self.database.get_conversation_history(user.id, limit=5)
					if h:
						text = "📜 Последние сообщения:\n\n"
						for i, entry in enumerate(h[-5:], 1):
							msg = entry["message"]
							if msg.get("type") == "text":
								val = msg["text"]
								text += f"{i}. {val[:50]}{'...' if len(val)>50 else ''}\n"
							elif msg.get("type") == "image":
								text += f"{i}. [Изображение]\n"
							elif msg.get("type") == "audio":
								text += f"{i}. [Голосовое сообщение]\n"
						await self._safe_edit_text(query.message, text, get_chat_keyboard())
					else:
						await query.message.answer("История пуста")
				elif data == "share":
					await query.message.answer("Функция будет добавлена позже")
				
				# АДМИН ПАНЕЛЬ
				elif data == "admin_panel" and user.id == ADMIN_USER_ID:
					stats = self.database.get_statistics()
					admin_text = (
						f"🔧 Админ-панель Uma Bot\n\n"
						f"📊 Статистика:\n"
						f"• Пользователей: {stats['total_users']}\n"
						f"• Активных сегодня: {stats['active_today']}\n"
						f"• Сообщений: {stats['total_messages']}\n\n"
						f"Выберите действие:"
					)
					await self._safe_edit_text(query.message, admin_text, get_admin_keyboard())
				elif data == "admin_broadcast" and user.id == ADMIN_USER_ID:
					await self._safe_edit_text(query.message, 
						"📢 Управление рассылками\n\n"
						"• Отправить рассылку всем пользователям\n"
						"• Запланировать рассылку\n"
						"• Просмотреть статистику рассылок\n\n"
						"Выберите действие:", get_admin_keyboard())
				elif data == "admin_message" and user.id == ADMIN_USER_ID:
					self.user_states[user.id] = "waiting_broadcast_message"
					await self._safe_edit_text(query.message,
						"✏️ Введите текст рассылки:\n\n"
						"Поддерживается Markdown форматирование:\n"
						"**жирный**, *курсив*, [ссылка](url)", get_admin_keyboard())
				elif data == "admin_scheduler" and user.id == ADMIN_USER_ID:
					self.user_states[user.id] = "waiting_schedule_time"
					await self._safe_edit_text(query.message,
						"🗓 Планировщик рассылок\n\n"
						"Введите время в формате:\n"
						"DD.MM.YYYY HH:MM\n\n"
						"Например: 15.08.2025 14:30", get_admin_keyboard())
				elif data == "admin_send_broadcast" and user.id == ADMIN_USER_ID:
					result = await self.scheduler.send_manual_broadcast("🚀 Тестовая рассылка от админа!")
					await self._safe_edit_text(query.message, f"✅ {result}", get_admin_keyboard())
				elif data == "admin_stats" and user.id == ADMIN_USER_ID:
					stats = self.database.get_statistics()
					stats_text = (
						f"📊 Подробная статистика\n\n"
						f"👥 Пользователи:\n"
						f"• Всего: {stats['total_users']}\n"
						f"• Активных сегодня: {stats['active_today']}\n"
						f"• Новых за неделю: {stats['new_this_week']}\n\n"
						f"💬 Сообщения:\n"
						f"• Всего: {stats['total_messages']}\n"
						f"• Текстовых: {stats['text_messages']}\n"
						f"• Изображений: {stats['image_messages']}\n"
						f"• Голосовых: {stats['audio_messages']}\n\n"
						f"📅 Активность:\n"
						f"• За сегодня: {stats['messages_today']}\n"
						f"• За неделю: {stats['messages_this_week']}"
					)
					await self._safe_edit_text(query.message, stats_text, get_admin_keyboard())
				elif data == "admin_back" and user.id == ADMIN_USER_ID:
					await self._safe_edit_text(query.message, "🔧 Админ-панель\n\nВыберите действие:", get_admin_keyboard())
			except Exception as e:
				logger.error(f"Ошибка в callback: {e}")
				# Не пытаемся отвечать на callback если уже произошла ошибка
				try:
					await query.message.answer("Произошла ошибка, попробуйте еще раз")
				except:
					pass

	async def run(self) -> None:
		# Стартуем планировщик и polling
		await self.scheduler.start_scheduler()
		await self.dp.start_polling(self.bot)

if __name__ == "__main__":
	async def _main():
		bot = UmaBot()
		await bot.run()
	asyncio.run(_main())
