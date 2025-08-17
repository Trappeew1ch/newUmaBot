import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging

class Database:
    def __init__(self, db_file: str = "database.json"):
        self.db_file = db_file
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """Загружает данные из файла"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"users": {}, "conversations": {}, "broadcasts": []}
        return {"users": {}, "conversations": {}, "broadcasts": []}
    
    def _save_data(self):
        """Сохраняет данные в файл"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None) -> None:
        """Добавляет нового пользователя"""
        data = self._load_data()
        user_id_str = str(user_id)
        
        if user_id_str not in data["users"]:
            data["users"][user_id_str] = {
                "username": username,
                "first_name": first_name,
                "registration_date": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat()
            }
        else:
            # Обновляем последнюю активность
            data["users"][user_id_str]["last_activity"] = datetime.now().isoformat()
            if username:
                data["users"][user_id_str]["username"] = username
            if first_name:
                data["users"][user_id_str]["first_name"] = first_name
        
        self._save_data()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получает информацию о пользователе"""
        return self.data["users"].get(str(user_id))
    
    def get_all_users(self) -> List[int]:
        """Получает список всех активных пользователей"""
        return [int(uid) for uid, user in self.data["users"].items() if user.get("is_active", True)]
    
    def add_message_to_conversation(self, user_id: int, message: Dict, response: str):
        """Добавляет сообщение в историю диалога"""
        user_key = str(user_id)
        if user_key not in self.data["conversations"]:
            self.data["conversations"][user_key] = []
        
        conversation_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message,
            "response": response
        }
        
        self.data["conversations"][user_key].append(conversation_entry)
        
        # Ограничиваем историю последними 50 сообщениями
        if len(self.data["conversations"][user_key]) > 50:
            self.data["conversations"][user_key] = self.data["conversations"][user_key][-50:]
        
        self._save_data()
    
    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Получает историю диалога пользователя"""
        user_key = str(user_id)
        if user_key not in self.data["conversations"]:
            return []
        
        return self.data["conversations"][user_key][-limit:]
    
    def clear_conversation(self, user_id: int):
        """Очищает историю диалога пользователя"""
        user_key = str(user_id)
        if user_key in self.data["conversations"]:
            self.data["conversations"][user_key] = []
            self._save_data()
    
    def add_broadcast(self, message: str, scheduled_time: str = None, sent: bool = False):
        """Добавляет рассылку"""
        broadcast = {
            "id": len(self.data["broadcasts"]) + 1,
            "message": message,
            "scheduled_time": scheduled_time,
            "sent": sent,
            "created_at": datetime.now().isoformat()
        }
        self.data["broadcasts"].append(broadcast)
        self._save_data()
        return broadcast["id"]
    
    def get_pending_broadcasts(self) -> List[Dict]:
        """Получает список ожидающих рассылок"""
        return [b for b in self.data["broadcasts"] if not b["sent"]]
    
    def mark_broadcast_sent(self, broadcast_id: int):
        """Отмечает рассылку как отправленную"""
        for broadcast in self.data["broadcasts"]:
            if broadcast["id"] == broadcast_id:
                broadcast["sent"] = True
                broadcast["sent_at"] = datetime.now().isoformat()
                break
        self._save_data()

    def get_statistics(self) -> dict:
        """Получает статистику для админ-панели"""
        try:
            data = self._load_data()
            from datetime import datetime, timedelta
            
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            
            total_users = len(data.get("users", {}))
            total_messages = 0
            text_messages = 0
            image_messages = 0
            audio_messages = 0
            active_today = 0
            new_this_week = 0
            messages_today = 0
            messages_this_week = 0
            
            # Подсчитываем статистику по пользователям
            for user_id, user_data in data.get("users", {}).items():
                # Активность сегодня
                if user_data.get("last_activity"):
                    last_activity = datetime.fromisoformat(user_data["last_activity"]).date()
                    if last_activity == today:
                        active_today += 1
                
                # Новые пользователи за неделю
                if user_data.get("registration_date"):
                    reg_date = datetime.fromisoformat(user_data["registration_date"]).date()
                    if reg_date >= week_ago:
                        new_this_week += 1
                
                # Сообщения пользователя
                conversation = data.get("conversations", {}).get(str(user_id), [])
                for entry in conversation:
                    if "message" in entry:
                        total_messages += 1
                        msg_type = entry["message"].get("type", "")
                        
                        if msg_type == "text":
                            text_messages += 1
                        elif msg_type == "image":
                            image_messages += 1
                        elif msg_type == "audio":
                            audio_messages += 1
                        
                        # Сообщения за сегодня и неделю
                        if "timestamp" in entry["message"]:
                            msg_date = datetime.fromisoformat(entry["message"]["timestamp"]).date()
                            if msg_date == today:
                                messages_today += 1
                            if msg_date >= week_ago:
                                messages_this_week += 1
            
            return {
                "total_users": total_users,
                "active_today": active_today,
                "new_this_week": new_this_week,
                "total_messages": total_messages,
                "text_messages": text_messages,
                "image_messages": image_messages,
                "audio_messages": audio_messages,
                "messages_today": messages_today,
                "messages_this_week": messages_this_week
            }
        except Exception as e:
            logging.error(f"Ошибка при получении статистики: {e}")
            return {
                "total_users": 0,
                "active_today": 0,
                "new_this_week": 0,
                "total_messages": 0,
                "text_messages": 0,
                "image_messages": 0,
                "audio_messages": 0,
                "messages_today": 0,
                "messages_this_week": 0
            }
