# 🚀 Развертывание Uma Bot

## 📋 Подготовка к развертыванию

### 1. Получение Telegram Bot Token
1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

### 2. Получение Groq API Key
1. Зарегистрируйтесь на [groq.com](https://groq.com)
2. Перейдите в раздел API Keys
3. Создайте новый API ключ
4. Скопируйте ключ

### 3. Получение Telegram User ID
1. Найдите @userinfobot в Telegram
2. Отправьте любое сообщение
3. Скопируйте ваш User ID

## 🖥️ Локальное развертывание

### Windows
```bash
# Установка Python (если не установлен)
# Скачайте с python.org

# Клонирование проекта
git clone <repository-url>
cd newUmaBot

# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка конфигурации
copy env.example .env
# Отредактируйте .env файл

# Запуск бота
python run.py
```

### macOS/Linux
```bash
# Клонирование проекта
git clone <repository-url>
cd newUmaBot

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка конфигурации
cp env.example .env
# Отредактируйте .env файл

# Запуск бота
python run.py
```

## ☁️ Облачное развертывание

### Heroku
```bash
# Установка Heroku CLI
# Скачайте с heroku.com

# Логин в Heroku
heroku login

# Создание приложения
heroku create your-uma-bot

# Настройка переменных окружения
heroku config:set GROQ_API_KEY=your_groq_api_key
heroku config:set TELEGRAM_BOT_TOKEN=your_telegram_token
heroku config:set ADMIN_USER_ID=your_user_id

# Развертывание
git push heroku main

# Запуск
heroku ps:scale worker=1
```

### Railway
```bash
# Установка Railway CLI
npm install -g @railway/cli

# Логин в Railway
railway login

# Инициализация проекта
railway init

# Настройка переменных окружения
railway variables set GROQ_API_KEY=your_groq_api_key
railway variables set TELEGRAM_BOT_TOKEN=your_telegram_token
railway variables set ADMIN_USER_ID=your_user_id

# Развертывание
railway up
```

### DigitalOcean App Platform
1. Создайте аккаунт на DigitalOcean
2. Перейдите в App Platform
3. Подключите GitHub репозиторий
4. Настройте переменные окружения
5. Разверните приложение

### VPS (Ubuntu/Debian)
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Python
sudo apt install python3 python3-pip python3-venv -y

# Клонирование проекта
git clone <repository-url>
cd newUmaBot

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка конфигурации
cp env.example .env
nano .env  # Отредактируйте файл

# Создание systemd сервиса
sudo nano /etc/systemd/system/uma-bot.service
```

Содержимое файла `/etc/systemd/system/uma-bot.service`:
```ini
[Unit]
Description=Uma Bot Telegram Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/newUmaBot
Environment=PATH=/path/to/newUmaBot/venv/bin
ExecStart=/path/to/newUmaBot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Запуск сервиса
sudo systemctl daemon-reload
sudo systemctl enable uma-bot
sudo systemctl start uma-bot

# Проверка статуса
sudo systemctl status uma-bot
```

## 🔧 Настройка веб-хуков (опционально)

### Для продакшена рекомендуется использовать веб-хуки:
```bash
# Установка веб-хука
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://your-domain.com/webhook"}'

# Удаление веб-хука (для возврата к polling)
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/deleteWebhook"
```

## 📊 Мониторинг

### Логи
```bash
# Просмотр логов systemd
sudo journalctl -u uma-bot -f

# Просмотр логов Heroku
heroku logs --tail

# Просмотр логов Railway
railway logs
```

### Статистика
- Используйте команду `/stats` в боте
- Проверяйте логи на ошибки
- Мониторьте использование API

## 🔒 Безопасность

### Рекомендации:
1. **Никогда не коммитьте** `.env` файл
2. Используйте **сильные пароли** для API ключей
3. **Регулярно обновляйте** зависимости
4. **Мониторьте** логи на подозрительную активность
5. Используйте **HTTPS** для веб-хуков

### Переменные окружения:
```bash
# Обязательные
GROQ_API_KEY=your_groq_api_key
TELEGRAM_BOT_TOKEN=your_telegram_token
ADMIN_USER_ID=your_user_id

# Опциональные
LOG_LEVEL=INFO
DATABASE_FILE=database.json
```

## 🚨 Устранение неполадок

### Частые проблемы:

1. **Бот не отвечает**
   - Проверьте правильность токена
   - Убедитесь, что бот не заблокирован
   - Проверьте логи на ошибки

2. **Ошибки API**
   - Проверьте правильность Groq API ключа
   - Убедитесь в наличии кредитов
   - Проверьте лимиты API

3. **Проблемы с зависимостями**
   - Обновите pip: `pip install --upgrade pip`
   - Переустановите зависимости: `pip install -r requirements.txt --force-reinstall`

4. **Проблемы с правами доступа**
   - Проверьте права на папку проекта
   - Убедитесь в правах на запись для базы данных

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи приложения
2. Убедитесь в правильности конфигурации
3. Проверьте подключение к интернету
4. Обратитесь к документации проекта

---

**Удачного развертывания!** 🚀

