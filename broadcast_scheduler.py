import asyncio
import logging
from datetime import datetime
import random
from database import Database
from keyboards import get_broadcast_keyboard
from config import DAILY_MESSAGES
from aiogram import Bot

class BroadcastScheduler:
	def __init__(self, bot: Bot, database: Database):
		self.bot = bot
		self.database = database
		self.logger = logging.getLogger(__name__)
		self.is_running = False
		self.task: asyncio.Task | None = None
	
	async def start_scheduler(self):
		if self.is_running:
			return
		self.is_running = True
		self.task = asyncio.create_task(self._scheduler_loop())
		self.logger.info("Планировщик рассылок запущен")
	
	async def stop_scheduler(self):
		self.is_running = False
		if self.task:
			self.task.cancel()
			try:
				await self.task
			except asyncio.CancelledError:
				pass
		self.logger.info("Планировщик рассылок остановлен")
	
	async def _scheduler_loop(self):
		while self.is_running:
			try:
				now = datetime.now()
				if now.hour == 10 and now.minute == 0:
					await self._send_daily_broadcast()
				await self._check_scheduled_broadcasts()
				await asyncio.sleep(60)
			except Exception as e:
				self.logger.error(f"Ошибка в планировщике: {e}")
				await asyncio.sleep(60)
	
	async def _send_daily_broadcast(self):
		try:
			message = random.choice(DAILY_MESSAGES)
			users = self.database.get_all_users()
			if not users:
				self.logger.info("Нет активных пользователей для ежедневной рассылки")
				return
			success_count = 0
			for user_id in users:
				try:
					await self.bot.send_message(chat_id=user_id, text=message, reply_markup=get_broadcast_keyboard())
					success_count += 1
					await asyncio.sleep(0.1)
				except Exception as e:
					self.logger.error(f"Ошибка отправки ежедневной рассылки пользователю {user_id}: {e}")
			self.logger.info(f"Ежедневная рассылка отправлена {success_count} пользователям из {len(users)}")
		except Exception as e:
			self.logger.error(f"Ошибка при отправке ежедневной рассылки: {e}")
	
	async def _check_scheduled_broadcasts(self):
		try:
			pending_broadcasts = self.database.get_pending_broadcasts()
			for broadcast in pending_broadcasts:
				if broadcast.get("scheduled_time"):
					scheduled_time = datetime.fromisoformat(broadcast["scheduled_time"])
					now = datetime.now()
					if now >= scheduled_time:
						await self._send_scheduled_broadcast(broadcast)
		except Exception as e:
			self.logger.error(f"Ошибка при проверке запланированных рассылок: {e}")
	
	async def _send_scheduled_broadcast(self, broadcast: dict):
		try:
			message = broadcast["message"]
			users = self.database.get_all_users()
			if not users:
				self.logger.info("Нет активных пользователей для запланированной рассылки")
				return
			success_count = 0
			for user_id in users:
				try:
					await self.bot.send_message(chat_id=user_id, text=message, reply_markup=get_broadcast_keyboard())
					success_count += 1
					await asyncio.sleep(0.1)
				except Exception as e:
					self.logger.error(f"Ошибка отправки запланированной рассылки пользователю {user_id}: {e}")
			self.database.mark_broadcast_sent(broadcast["id"])
			self.logger.info(f"Запланированная рассылка {broadcast['id']} отправлена {success_count} пользователям")
		except Exception as e:
			self.logger.error(f"Ошибка при отправке запланированной рассылки: {e}")
	
	async def send_manual_broadcast(self, message: str, user_id: int | None = None) -> str:
		try:
			users = self.database.get_all_users()
			if user_id:
				users = [user_id]
			if not users:
				return "Нет активных пользователей для рассылки"
			success_count = 0
			for uid in users:
				try:
					await self.bot.send_message(chat_id=uid, text=message, reply_markup=get_broadcast_keyboard())
					success_count += 1
					await asyncio.sleep(0.1)
				except Exception as e:
					self.logger.error(f"Ошибка отправки ручной рассылки пользователю {uid}: {e}")
			return f"Рассылка отправлена {success_count} пользователям из {len(users)}"
		except Exception as e:
			self.logger.error(f"Ошибка при отправке ручной рассылки: {e}")
			return f"Ошибка при отправке рассылки: {e}"
