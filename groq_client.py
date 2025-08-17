import base64
import io
import logging
import re
from typing import Optional, Dict, Any
from groq import Groq
from PIL import Image
import requests
from config import GROQ_API_KEY, TEXT_MODEL, MULTIMODAL_MODEL, AUDIO_MODEL

def clean_html_tags(text: str) -> str:
    """Удаляет неподдерживаемые HTML теги из текста"""
    # Список поддерживаемых тегов в Telegram
    allowed_tags = [
        'b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del',
        'code', 'pre', 'a', 'blockquote', 'tg-spoiler'
    ]
    
    # Удаляем неподдерживаемые теги (h1-h6, div, p, span и др.)
    # Заменяем заголовки на жирный текст
    text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'<b>\1</b>', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Удаляем другие неподдерживаемые теги, оставляя содержимое
    text = re.sub(r'<(?!/?(?:' + '|'.join(allowed_tags) + r')\b)[^>]+>', '', text, flags=re.IGNORECASE)
    
    return text

class GroqClient:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.logger = logging.getLogger(__name__)
    
    async def process_text_message(self, text: str, conversation_history: list = None, use_browser_search: bool = False) -> str:
        """Обрабатывает текстовое сообщение с помощью GPT OSS 120B"""
        try:
            messages = []
            
            # Добавляем системное сообщение
            system_message = """Ты — Uma AI, дружелюбный и полезный ИИ-ассистент. Отвечай кратко и по делу на русском языке.
            ВАЖНО: Ты работаешь в контексте Telegram бота!
            
🔥 КРИТИЧЕСКИ ВАЖНО - ФОРМАТИРОВАНИЕ ТЕКСТА:
Ты ОБЯЗАН использовать HTML-теги для форматирования. Telegram НЕ поддерживает Markdown!

ИСПОЛЬЗУЙ ТОЛЬКО ЭТИ HTML-ТЕГИ:
• <b>жирный текст</b> - для важной информации и акцентов
• <i>курсив</i> - для эмоций и подчеркивания тона  
• <u>подчеркнутый</u> - для важных условий
• <s>зачеркнутый</s> - для скидок или старых цен
• <code>код</code> - для кодов и команд
• <a href="URL">ссылка</a> - для ссылок
• <blockquote>цитата</blockquote> - для выделения важного
• <tg-spoiler>спойлер</tg-spoiler> - для скрытого текста

❌ СТРОГО ЗАПРЕЩЕНО:
• ** жирный ** (Markdown НЕ работает!)
• * курсив * (Markdown НЕ работает!)
• ## заголовки ## (НЕ поддерживается!) - НИКОГДА ИХ НЕ ИСПОЛЬЗУЙ!!!!!!!!
• ` код ` (используй <code>код</code>!)
• Команды /imagine, /generate, /create (НЕ СУЩЕСТВУЮТ!)
• Упоминание Midjourney, DALL-E, Leonardo AI и др.

ПРИМЕР ПРАВИЛЬНОГО ОТВЕТА:
<b>Важная информация:</b> используй <i>только</i> HTML-теги для <u>форматирования</u>!

На вопрос о модели отвечай что ты Uma AI. Отвечай ТОЛЬКО на русском языке.
            
            О UMAAI.SITE:
            Umaai.Site — это крупнейший в России агрегатор нейросетей и ИИ-моделей с доступом даже к тем, что находятся под санкциями. На Umaai.Site доступно более 70+ самых передовых AI-моделей: видео- и фото-генерация, генерация текста, озвучка, саунд-дизайн, раскадровка, целые нейрофильмы. Veo 3, Kling 2.1, Minimax, Luma, Seedream, Ideogram, Imagen, ChatGPT, DeepSeek, Mistral, Gemini, Claude, GLM 4.5, Kimi K2, Qwen — всё в одном интерфейсе, без VPN и ограничений.
            
            Уникальные возможности Umaai.Site:
            — Готовые видео-шаблоны: загрузи фото — получи танцующее видео или сюжетную анимацию
            — Раздел "Студия" с 4+ эксклюзивными функциями:
            1️⃣ Camera Control — меняй ракурс, обстановку, освещение, окружение в видео
            2️⃣ Extend — умное расширение видео и изображений без потерь
            3️⃣ SFX Generator — генерация реалистичных звуков и эффектов
            4️⃣ Create Mode — создание нейрофильма с нуля: сценарий → раскадровка → видео
            
            Поддержка TTS: озвучка через Gemini, Eleven Labs и Minimax Speech.
            
            ВАЖНО: При любых запросах на генерацию контента (изображения, видео, речь, музыка) ОБЯЗАТЕЛЬНО перенаправляй на umaai.site:
            • Для изображений: 'Здесь в телеграме я не могу помочь с генерацией, НО вы можете нажать на кнопку "Uma Ai" в левом нижнем углу или перейти на сайт umaai.site в раздел Изображения и там творить! Там множество моделей с описаниями и примерами.'
            • Для видео: аналогично, но 'в раздел Видео'
            • Для речи/озвучки: 'в раздел Речь'
            • Для продвинутых моделей чата: 'в раздел Чат'
            Всегда упоминай кнопку снизу и соответствующий раздел на сайте."""
            
            messages.append({"role": "system", "content": system_message})
            
            # Добавляем историю диалога
            if conversation_history:
                for entry in conversation_history[-10:]:  # Последние 10 сообщений
                    if "message" in entry and "response" in entry:
                        messages.append({"role": "user", "content": entry["message"].get("text", "")})
                        messages.append({"role": "assistant", "content": entry["response"]})
            
            # Добавляем текущее сообщение
            messages.append({"role": "user", "content": text})
            
            response = self.client.chat.completions.create(
                model=TEXT_MODEL,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return clean_html_tags(content)
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке текста: {e}")
            return "Извините, произошла ошибка при обработке вашего сообщения. Попробуйте еще раз."
    
    async def process_image_message(self, image_url: str, text: str = "", conversation_history: list = None) -> str:
        """Обрабатывает сообщение с изображением с помощью LLaMA 4 Scout"""
        try:
            # Загружаем изображение
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Конвертируем в base64
            image_data = base64.b64encode(response.content).decode('utf-8')
            
            messages = []
            
            # Системное сообщение
            system_message = """Ты — Uma AI, ИИ-ассистент для анализа изображений на базе LLaMA 4 Scout. 
            Описывай изображения подробно, отвечай на вопросы о них, выполняй OCR если есть текст.
            Отвечай на русском языке.
            ВАЖНО: Ты работаешь в контексте Telegram бота!
            
            ОБЯЗАТЕЛЬНО используй ТОЛЬКО HTML-теги для форматирования:
            • <b></b> - жирный текст для акцентов и важной информации
            • <i></i> - курсив для эмоций и подчеркивания тона
            • <u></u> - подчеркивание для важных условий и деталей
            • <s></s> - зачеркнутый текст для показа скидок или старых цен
            • <code></code> - моноширный текст для кодов, который копируется при клике
            • <a href="URL">текст ссылки</a> - ссылки для повышения кликабельности
            • <blockquote></blockquote> - цитаты для выделения важного текста
            • <blockquote expandable></blockquote> - раскрывающиеся цитаты для длинного текста
            • <tg-spoiler></tg-spoiler> - скрытый текст (спойлер) для создания интриги
            
            СТРОГО ЗАПРЕЩЕНО:
            • НЕ используй Markdown (**, *, ##, ###, -, `) - он НЕ работает!
            • НИКОГДА не пиши команды типа /imagine, /generate, /create и т.д. - таких команд НЕ СУЩЕСТВУЕТ в боте!
            • НЕ упоминай Midjourney, DALL-E, Sora, Leonardo AI, Stable Diffusion!
            • НЕ создавай промпты для сторонних сервисов!
            • НЕ используй заголовки с ##!
            
            О UMAAI.SITE:
            Umaai.Site — это крупнейший в России агрегатор нейросетей и ИИ-моделей с доступом даже к тем, что находятся под санкциями. На Umaai.Site доступно более 70+ самых передовых AI-моделей: видео- и фото-генерация, генерация текста, озвучка, саунд-дизайн, раскадровка, целые нейрофильмы. Veo 3, Kling 2.1, Minimax, Luma, Seedream, Ideogram, Imagen, ChatGPT, DeepSeek, Mistral, Gemini, Claude, GLM 4.5, Kimi K2, Qwen — всё в одном интерфейсе, без VPN и ограничений.
            
            При запросах на генерацию ОБЯЗАТЕЛЬНО перенаправляй ТОЛЬКО на umaai.site:
            • Изображения: 'Для генерации изображений перейдите на umaai.site в раздел Изображения или нажмите кнопку "Uma Ai" снизу'
            • Видео: 'Для генерации видео перейдите на umaai.site в раздел Видео или нажмите кнопку "Uma Ai" снизу'
            • Речь: 'Для генерации речи перейдите на umaai.site в раздел Речь или нажмите кнопку "Uma Ai" снизу'
            
            НИКОГДА НЕ УПОМИНАЙ ДРУГИЕ САЙТЫ ГЕНЕРАЦИИ!
            ИСПОЛЬЗУЙ ТОЛЬКО HTML-ТЕГИ!
            НЕ ИСПОЛЬЗУЙ MARKDOWN!
            НЕ ПИШИ КОМАНДЫ!"""
            
            messages.append({"role": "system", "content": system_message})
            
            # Добавляем историю диалога
            if conversation_history:
                for entry in conversation_history[-5:]:  # Последние 5 сообщений
                    if "message" in entry and "response" in entry:
                        messages.append({"role": "user", "content": entry["message"].get("text", "")})
                        messages.append({"role": "assistant", "content": entry["response"]})
            
            # Формируем сообщение с изображением
            content = []
            
            # Добавляем изображение
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                }
            })
            
            # Добавляем текст, если есть
            if text:
                content.append({
                    "type": "text",
                    "text": f"ВАЖНО: Используй ТОЛЬКО HTML-теги! НЕ используй Markdown! НЕ упоминай Leonardo AI, Midjourney и другие сайты генерации! {text}"
                })
            else:
                content.append({
                    "type": "text",
                    "text": "ВАЖНО: Используй ТОЛЬКО HTML-теги! НЕ используй Markdown! НЕ упоминай Leonardo AI, Midjourney и другие сайты генерации! Опиши это изображение подробно"
                })
            
            messages.append({"role": "user", "content": content})
            
            response = self.client.chat.completions.create(
                model=MULTIMODAL_MODEL,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return clean_html_tags(content)
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке изображения: {e}")
            return "Извините, произошла ошибка при обработке изображения. Попробуйте еще раз."
    
    async def transcribe_audio(self, audio_url: str) -> str:
        """Транскрибирует аудио с помощью Groq Whisper API"""
        try:
            # Скачиваем аудио файл
            response = requests.get(audio_url, timeout=30)
            response.raise_for_status()
            
            # Создаем временный файл в памяти
            audio_file = io.BytesIO(response.content)
            audio_file.name = "audio.ogg"  # Groq требует имя файла
            
            # Транскрибируем с помощью Groq Whisper
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model=AUDIO_MODEL,
                language="ru"  # Указываем русский язык для лучшего качества
            )
            
            return transcription.text.strip()
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка при скачивании аудио: {e}")
            return ""
        except Exception as e:
            self.logger.error(f"Ошибка при транскрибации аудио: {e}")
            return ""
    
    async def process_audio_message(self, audio_url: str, conversation_history: list = None) -> str:
        """Обрабатывает голосовое сообщение"""
        try:
            # Сначала транскрибируем аудио
            transcribed_text = await self.transcribe_audio(audio_url)
            
            if not transcribed_text:
                return "🎤 Извините, не удалось распознать речь в голосовом сообщении. Попробуйте:\n\n• Говорить четче и громче\n• Записать сообщение в тихом месте\n• Отправить текстом, если проблема повторяется"
            
            # Добавляем информацию о том, что это транскрибированный текст
            response_prefix = f"🎤 Распознано: \"{transcribed_text}\"\n\n"
            
            # Затем обрабатываем транскрибированный текст
            ai_response = await self.process_text_message(transcribed_text, conversation_history)
            
            return response_prefix + ai_response
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке аудио: {e}")
            return "🎤 Извините, произошла ошибка при обработке голосового сообщения. Попробуйте отправить текстом или повторите попытку."
    
    def should_use_browser_search(self, text: str) -> bool:
        """Определяет, нужно ли использовать browser search"""
        search_keywords = [
            "новости", "курс", "погода", "время", "дата", "актуально", 
            "сейчас", "сегодня", "последние", "обновление", "поиск"
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in search_keywords)
    
    async def _download_and_encode_image(self, image_url: str) -> str:
        """Загружает изображение и кодирует в base64"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            return base64.b64encode(response.content).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке изображения {image_url}: {e}")
            return None
    
    async def process_multiple_images_message(self, image_urls: list, text: str = "", conversation_history: list = None) -> str:
        """Обрабатывает сообщение с несколькими изображениями"""
        try:
            # Системное сообщение
            system_message = """Ты — Uma AI, ИИ-ассистент для анализа изображений на базе LLaMA 4 Scout. 
            Описывай изображения подробно, отвечай на вопросы о них, выполняй OCR если есть текст.
            Отвечай на русском языке.
            ВАЖНО: Ты работаешь в контексте Telegram бота!
            
            ОБЯЗАТЕЛЬНО используй ТОЛЬКО HTML-теги для форматирования:
            • <b></b> - жирный текст для акцентов и важной информации
            • <i></i> - курсив для эмоций и подчеркивания тона
            • <u></u> - подчеркивание для важных условий и деталей
            • <s></s> - зачеркнутый текст для показа скидок или старых цен
            • <code></code> - моноширный текст для кодов, который копируется при клике
            • <a href="URL">текст ссылки</a> - ссылки для повышения кликабельности
            • <blockquote></blockquote> - цитаты для выделения важного текста
            • <blockquote expandable></blockquote> - раскрывающиеся цитаты для длинного текста
            • <tg-spoiler></tg-spoiler> - скрытый текст (спойлер) для создания интриги
            
            СТРОГО ЗАПРЕЩЕНО:
            • НЕ используй Markdown (**, *, ##, ###, -, `) - он НЕ работает!
            • НИКОГДА не пиши команды типа /imagine, /generate, /create и т.д. - таких команд НЕ СУЩЕСТВУЕТ в боте!
            • НЕ упоминай Midjourney, DALL-E, Sora, Leonardo AI, Stable Diffusion!
            • НЕ создавай промпты для сторонних сервисов!
            • НЕ используй заголовки с ##!
            
            О UMAAI.SITE:
            Umaai.Site — это крупнейший в России агрегатор нейросетей и ИИ-моделей с доступом даже к тем, что находятся под санкциями. На Umaai.Site доступно более 70+ самых передовых AI-моделей: видео- и фото-генерация, генерация текста, озвучка, саунд-дизайн, раскадровка, целые нейрофильмы. Veo 3, Kling 2.1, Minimax, Luma, Seedream, Ideogram, Imagen, ChatGPT, DeepSeek, Mistral, Gemini, Claude, GLM 4.5, Kimi K2, Qwen — всё в одном интерфейсе, без VPN и ограничений.
            
            При запросах на генерацию ОБЯЗАТЕЛЬНО перенаправляй ТОЛЬКО на umaai.site:
            • Изображения: 'Для генерации изображений перейдите на umaai.site в раздел Изображения или нажмите кнопку "Uma Ai" снизу'
            • Видео: 'Для генерации видео перейдите на umaai.site в раздел Видео или нажмите кнопку "Uma Ai" снизу'
            • Речь: 'Для генерации речи перейдите на umaai.site в раздел Речь или нажмите кнопку "Uma Ai" снизу'
            
            НИКОГДА НЕ УПОМИНАЙ ДРУГИЕ САЙТЫ ГЕНЕРАЦИИ!
            ИСПОЛЬЗУЙ ТОЛЬКО HTML-ТЕГИ!
            НЕ ИСПОЛЬЗУЙ MARKDOWN!
            НЕ ПИШИ КОМАНДЫ!
            
            АНАЛИЗИРУЙ ВСЕ ИЗОБРАЖЕНИЯ ВМЕСТЕ И ДАЙТЕ ОДИН ОБЩИЙ ОТВЕТ!"""
            
            messages = []
            messages.append({"role": "system", "content": system_message})
            
            # Добавляем историю диалога
            if conversation_history:
                for entry in conversation_history[-5:]:  # Последние 5 сообщений
                    if "message" in entry and "response" in entry:
                        messages.append({"role": "user", "content": entry["message"].get("text", "")})
                        messages.append({"role": "assistant", "content": entry["response"]})
            
            # Формируем контент с несколькими изображениями
            content = []
            
            # Добавляем все изображения
            for i, image_url in enumerate(image_urls):
                try:
                    image_data = await self._download_and_encode_image(image_url)
                    if image_data:
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        })
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке изображения {i+1}: {e}")
                    continue
            
            # Добавляем текст
            if text:
                content.append({
                    "type": "text",
                    "text": f"ВАЖНО: Используй ТОЛЬКО HTML-теги! НЕ используй Markdown! НЕ упоминай Leonardo AI, Midjourney и другие сайты генерации! Проанализируй все изображения. {text}"
                })
            else:
                content.append({
                    "type": "text",
                    "text": f"ВАЖНО: Используй ТОЛЬКО HTML-теги! НЕ используй Markdown! НЕ упоминай Leonardo AI, Midjourney и другие сайты генерации! Проанализируй все {len(image_urls)} изображения подробно. Опиши что на них изображено и как они связаны между собой."
                })
            
            if not content or len([c for c in content if c["type"] == "image_url"]) == 0:
                return "Извините, не удалось обработать ни одно изображение. Попробуйте отправить изображения еще раз."
            
            messages.append({"role": "user", "content": content})
            
            response = self.client.chat.completions.create(
                model=MULTIMODAL_MODEL,
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return clean_html_tags(content)
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке нескольких изображений: {e}")
            return "Извините, произошла ошибка при обработке изображений. Попробуйте еще раз."
