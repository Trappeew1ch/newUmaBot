#!/usr/bin/env python3
"""
Uma Bot - Запуск
Простой скрипт для запуска Telegram-бота Uma Bot
"""

import sys
import os
import subprocess

def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    required_packages = [
        'telegram',
        'groq',
        'python-dotenv',
        'requests',
        'Pillow'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Отсутствуют необходимые пакеты:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n📦 Установите зависимости командой:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def check_config():
    """Проверяет наличие файла конфигурации"""
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("\n📝 Создайте файл .env на основе env.example:")
        print("   cp env.example .env")
        print("\n🔧 Затем отредактируйте .env и укажите:")
        print("   - Ваш Telegram User ID в ADMIN_USER_ID")
        return False
    
    return True

def main():
    """Основная функция запуска"""
    print("🤖 Uma Bot - Запуск")
    print("=" * 30)
    
    # Проверяем зависимости
    print("🔍 Проверка зависимостей...")
    if not check_dependencies():
        sys.exit(1)
    print("✅ Зависимости установлены")
    
    # Проверяем конфигурацию
    print("🔍 Проверка конфигурации...")
    if not check_config():
        sys.exit(1)
    print("✅ Конфигурация найдена")
    
    # Запускаем бота
    print("🚀 Запуск Uma Bot...")
    try:
        from main import UmaBot
        bot = UmaBot()
        bot.run()
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

