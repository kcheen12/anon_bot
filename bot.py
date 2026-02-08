#!/usr/bin/env python3
import os
import sys
import time
import logging
import sqlite3
import asyncio
from threading import Thread
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ====== КОНФИГУРАЦИЯ ======
# Получаем токен из переменных окружения (обязательно!)
BOT_TOKEN = os.environ.get('BOT_TOKEN')

# Проверяем, что токен установлен
if not BOT_TOKEN:
    print("❌ ОШИБКА: Переменная окружения BOT_TOKEN не установлена!")
    print("ℹ️  На Render добавьте переменную BOT_TOKEN в настройках сервиса")
    sys.exit(1)

# Маскируем токен для безопасного логирования
MASKED_TOKEN = BOT_TOKEN[:10] + "..." + BOT_TOKEN[-5:] if len(BOT_TOKEN) > 15 else "***"

ADMINS = [
    7976904182,  # я
    5410696822,  # лиза
    7032286132,  # жан
    7607540379,  # нари
    6806766903,  # тсунэтами
]

YOUR_ID = 7976904182  # Ваш ID для специальных команд

forward_map = {}

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== БАЗА ДАННЫХ ======
def init_db():
    """Инициализация базы данных"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")

def save_user(user):
    """Сохранение пользователя в базу данных"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user.id, user.username, user.first_name, user.last_name))
        conn.commit()
        conn.close()
        logger.info(f"📝 Сохранен пользователь {user.id}")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения пользователя {user.id}: {e}")

def get_all_users():
    """Получение всех пользователей из базы данных"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, first_name, last_name FROM users')
        users = cursor.fetchall()
        conn.close()
        return users
    except Exception as e:
        logger.error(f"❌ Ошибка получения пользователей: {e}")
        return []

def get_user_count():
    """Получение количества пользователей"""
    try:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        logger.error(f"❌ Ошибка получения количества пользователей: {e}")
        return 0

# ====== ТЕЛЕГРАМ БОТ ======
# Глобальная переменная для приложения
application = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user = update.effective_user
    
    # Сохраняем пользователя в БД
    save_user(user)
    
    await update.message.reply_text(
        "*KEEP IT QUIET*\n\n"
        "Бот для проверки возраста.\n"
        "Возрастное ограничение составляет 15+. Отправь фото любого документа, подтверждающего возраст (нужна только дата рождения, не более). Также на фото должна быть бумажка с вашим ником. Данные не выходят за рамки чата, не используются в личных целях.\n\n"
        "По тех вопросам/неполадкам: @SexPriest",
        parse_mode="Markdown"
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка сообщения всем пользователям (только для вас)"""
    user = update.effective_user
    
    # Проверка прав
    if user.id != YOUR_ID:
        await update.message.reply_text("❌ У вас нет прав для использования этой команды.")
        return
    
    # Проверка наличия текста
    if not context.args:
        await update.message.reply_text(
            "📢 Использование команды:\n"
            "/broadcast ваш_текст\n\n"
            "Пример: /broadcast Привет всем! Это тестовое сообщение."
        )
        return
    
    message_text = ' '.join(context.args)
    
    # Получаем всех пользователей
    users = get_all_users()
    total_users = len(users)
    
    if total_users == 0:
        await update.message.reply_text("❌ В базе данных нет пользователей.")
        return
    
    # Отправляем сообщение о начале рассылки
    status_msg = await update.message.reply_text(
        f"📤 Начинаю рассылку для {total_users} пользователей...\n"
        f"Сообщение: {message_text[:100]}..."
    )
    
    # Статистика
    success_count = 0
    fail_count = 0
    fail_details = []
    
    # Отправка сообщений
    for i, (user_id, username, first_name, last_name) in enumerate(users, 1):
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 *Объявление от администратора:*\n\n{message_text}",
                parse_mode="Markdown"
            )
            success_count += 1
            
            # Обновляем статус каждые 10 отправок
            if i % 10 == 0 or i == total_users:
                await status_msg.edit_text(
                    f"📤 Рассылка: {i}/{total_users}\n"
                    f"✅ Успешно: {success_count}\n"
                    f"❌ Ошибок: {fail_count}"
                )
            
            # Небольшая задержка
            await asyncio.sleep(0.1)
            
        except Exception as e:
            fail_count += 1
            fail_details.append(f"ID {user_id}: {str(e)[:50]}")
            logger.error(f"Не удалось отправить пользователю {user_id}: {e}")
    
    # Финальный отчет
    report = f"✅ Рассылка завершена!\n\n"
    report += f"📊 Статистика:\n"
    report += f"• Всего пользователей: {total_users}\n"
    report += f"• Успешно отправлено: {success_count}\n"
    report += f"• Не удалось отправить: {fail_count}\n"
    
    if fail_count > 0 and fail_count <= 5:
        report += f"\n❌ Ошибки:\n" + "\n".join(fail_details)
    
    await status_msg.edit_text(report)

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику пользователей (только для вас)"""
    user = update.effective_user
    
    # Проверка прав
    if user.id != YOUR_ID:
        await update.message.reply_text("❌ У вас нет прав для использования этой команды.")
        return
    
    # Получаем статистику
    total_users = get_user_count()
    users = get_all_users()[:10]
    
    if total_users == 0:
        await update.message.reply_text("📊 В базе данных пока нет пользователей.")
        return
    
    # Формируем сообщение
    message = f"📊 *Статистика пользователей*\n\n"
    message += f"• Всего пользователей: *{total_users}*\n\n"
    message += f"*Последние 10 пользователей:*\n"
    
    for i, (user_id, username, first_name, last_name) in enumerate(users, 1):
        name = f"{first_name or ''} {last_name or ''}".strip() or "Без имени"
        username_str = f"@{username}" if username else "нет username"
        message += f"{i}. {name} ({username_str}) - ID: `{user_id}`\n"
    
    message += f"\n👑 Админов: {len(ADMINS)}"
    message += f"\n🆔 Ваш ID: `{user.id}`"
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений от обычных пользователей"""
    user = update.effective_user
    
    # Сохраняем пользователя в БД
    save_user(user)
    
    # Пропускаем админов
    if user.id in ADMINS:
        return
    
    msg = update.message
    if msg.text and msg.text.startswith('/'):
        return
    
    try:
        for admin_id in ADMINS:
            try:
                sent_message = None
                
                if msg.photo:
                    sent_message = await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=msg.photo[-1].file_id,
                        caption=f"*Анонер {user.id}*\n\n{msg.caption if msg.caption else ''}\n\n",
                        parse_mode="Markdown"
                    )
                elif msg.text:
                    sent_message = await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"*Анонер {user.id}*\n\n{msg.text}\n\n",
                        parse_mode="Markdown"
                    )
                else:
                    sent_message = await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"*Анонер {user.id}*\n\nФайл/Медиа\n\n",
                        parse_mode="Markdown"
                    )
                
                if sent_message:
                    forward_map[sent_message.message_id] = (user.id, msg.message_id)
                    logger.info(f"Сохранил связь: {sent_message.message_id} → {user.id}")
                
            except Exception as e:
                logger.error(f"Не удалось отправить админу {admin_id}: {e}")
        
        await msg.reply_text(
            "Сообщение отправлено всем админам, не спамь. "
            "Как получишь ответ - отпишись сообщением, чтобы уведомить остальных >.<"
        )
    
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await msg.reply_text("Ошибка, попробуй позже")

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ответов от админов"""
    user = update.effective_user
    msg = update.message
    
    if user.id not in ADMINS:
        return
    
    if msg.text and msg.text.startswith('/'):
        return
    
    if not msg.reply_to_message:
        logger.info(f"Сообщение админа {user.id} не является ответом")
        return
    
    replied_msg_id = msg.reply_to_message.message_id
    
    if replied_msg_id in forward_map:
        target_user_id, target_message_id = forward_map[replied_msg_id]
        
        try:
            if msg.text:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"*Ответ админа:*\n\n{msg.text}",
                    parse_mode="Markdown",
                    reply_to_message_id=target_message_id
                )
            elif msg.photo:
                await context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=msg.photo[-1].file_id,
                    caption=f"*Ответ админа:*\n\n{msg.caption if msg.caption else ''}",
                    parse_mode="Markdown",
                    reply_to_message_id=target_message_id
                )
            else:
                await context.bot.copy_message(
                    chat_id=target_user_id,
                    from_chat_id=msg.chat_id,
                    message_id=msg.message_id,
                    reply_to_message_id=target_message_id
                )
            
            await msg.reply_text(f"✅ Ответ отправлен анонеру")
            
        except Exception as e:
            logger.error(f"Ошибка отправки анонеру {target_user_id}: {e}")
            await msg.reply_text(f"❌ Не удалось отправить пользователю: {e}")
    
    else:
        await msg.reply_text(
            "Это сообщение не является пересланным от пользователя или устарело.\n\n"
            "Как ответить пользователю:\n"
            "1. Найдите сообщение от бота с текстом 'Анонер {id}'\n"
            "2. Нажмите 'Ответить' на него\n"
            "3. Напишите текст\n\n"
            "Бот отправит ответ анонимно.",
            parse_mode="Markdown"
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке обновления: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("Произошла ошибка. Попробуйте позже.")

def create_telegram_app():
    """Создание и настройка приложения Telegram"""
    global application
    
    print(f"\n{'='*60}")
    print(f"🚀 ЗАПУСК ТЕЛЕГРАМ БОТА (PTB v20)")
    print(f"{'='*60}")
    print(f"⏰ Время: {time.ctime()}")
    print(f"🔐 Токен: {MASKED_TOKEN}")
    print(f"👑 Админов: {len(ADMINS)}")
    print(f"🆔 Ваш ID: {YOUR_ID}")
    
    # Инициализация базы данных
    init_db()
    print(f"📊 Пользователей в базе: {get_user_count()}")
    
    try:
        # Создаем приложение Telegram с новым API
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .pool_timeout(30.0)
            .build()
        )
        
        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("broadcast", broadcast))
        application.add_handler(CommandHandler("users", users_command))
        
        # Добавляем обработчики сообщений
        # Для обычных пользователей (не админов)
        user_filters = filters.ALL & ~filters.User(user_id=ADMINS)
        application.add_handler(MessageHandler(
            user_filters & filters.TEXT & ~filters.COMMAND,
            handle_user_message
        ))
        application.add_handler(MessageHandler(
            user_filters & filters.PHOTO,
            handle_user_message
        ))
        
        # Для админов (только ответы)
        admin_filters = filters.User(user_id=ADMINS) & ~filters.COMMAND
        application.add_handler(MessageHandler(
            admin_filters,
            handle_admin_reply
        ))
        
        print("✅ Telegram бот инициализирован (PTB v20)")
        return application
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания приложения: {e}")
        raise

# ====== FLASK APP ДЛЯ WEBHOOK ======
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    """Домашняя страница"""
    user_count = get_user_count()
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Bot</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ 
                font-family: 'Arial', sans-serif; 
                text-align: center; 
                padding: 50px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }}
            .container {{
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                padding: 40px;
                border-radius: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                max-width: 600px;
                width: 90%;
            }}
            h1 {{ 
                font-size: 2.5em; 
                margin-bottom: 20px; 
                color: white;
            }}
            .status {{ 
                color: #4ade80; 
                font-size: 1.5em; 
                font-weight: bold;
                margin: 20px 0;
            }}
            .info {{ 
                margin-top: 20px; 
                color: rgba(255, 255, 255, 0.9);
                font-size: 1.1em;
                line-height: 1.6;
            }}
            .stats {{
                background: rgba(255, 255, 255, 0.15);
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
            }}
            .btn {{
                display: inline-block;
                padding: 12px 30px;
                background: #4ade80;
                color: white;
                text-decoration: none;
                border-radius: 50px;
                font-weight: bold;
                margin-top: 20px;
                transition: transform 0.3s, background 0.3s;
            }}
            .btn:hover {{
                background: #22c55e;
                transform: translateY(-2px);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Telegram Bot</h1>
            <div class="status">✅ Бот активен и работает</div>
            <div class="stats">
                <p>👥 Пользователей в базе: <strong>{user_count}</strong></p>
                <p>👑 Администраторов: <strong>{len(ADMINS)}</strong></p>
                <p>⚡ Режим: <strong>Webhook</strong></p>
            </div>
            <div class="info">
                <p>Бот для анонимной связи с администраторами</p>
                <p>Возрастная проверка • Конфиденциальность • Безопасность</p>
                <a href="/health" class="btn">Проверить здоровье системы</a>
            </div>
        </div>
    </body>
    </html>
    '''

@flask_app.route('/health')
def health():
    """Проверка здоровья для Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'users_count': get_user_count(),
        'bot_token_set': bool(BOT_TOKEN),
        'token_length': len(BOT_TOKEN) if BOT_TOKEN else 0,
        'bot': 'webhook',
        'version': '3.0',
        'platform': 'python-telegram-bot v20',
        'environment': 'production' if 'RENDER' in os.environ else 'development'
    }), 200

@flask_app.route('/webhook', methods=['POST'])
async def webhook():
    """Endpoint для получения обновлений от Telegram"""
    try:
        if not application:
            logger.error("Bot application not initialized")
            return jsonify({'status': 'error', 'message': 'Bot not initialized'}), 500
        
        # Получаем данные от Telegram
        json_data = request.get_json(force=True)
        
        if not json_data:
            logger.error("Empty webhook data received")
            return jsonify({'status': 'error', 'message': 'Empty data'}), 400
        
        # Создаем обновление
        update = Update.de_json(json_data, application.bot)
        
        # Инициализируем и обрабатываем
        await application.initialize()
        await application.process_update(update)
        
        logger.info(f"Webhook processed successfully")
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500

def setup_webhook():
    """Настройка webhook"""
    global application
    
    # Даем время Flask запуститься
    time.sleep(5)
    
    # Получаем URL для webhook
    render_external_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    render_app_name = os.environ.get('RENDER_APP_NAME', '')
    
    if render_external_url:
        webhook_url = f"{render_external_url}/webhook"
    elif render_app_name:
        webhook_url = f"https://{render_app_name}.onrender.com/webhook"
    else:
        port = int(os.environ.get('PORT', 8080))
        webhook_url = f"http://localhost:{port}/webhook"
        print(f"⚠️  Локальный режим: {webhook_url}")
    
    print(f"\n🌐 Настройка Webhook:")
    print(f"   URL: {webhook_url}")
    
    try:
        # Используем асинхронный вызов для установки webhook
        async def async_setup():
            # Удаляем старый webhook
            await application.bot.delete_webhook(drop_pending_updates=True)
            await asyncio.sleep(2)
            
            # Устанавливаем новый webhook
            await application.bot.set_webhook(
                url=webhook_url,
                max_connections=40,
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query', 'chat_member']
            )
            
            print("✅ Webhook успешно установлен")
            
            # Получаем информацию о webhook
            webhook_info = await application.bot.get_webhook_info()
            print(f"ℹ️  Информация о webhook:")
            print(f"   URL: {webhook_info.url}")
            print(f"   Ожидает обновлений: {webhook_info.pending_update_count}")
            print(f"   Активен: {webhook_info.url == webhook_url}")
        
        # Запускаем асинхронную функцию
        asyncio.run(async_setup())
        
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")
        print("🔄 Повторная попытка через 10 секунд...")
        time.sleep(10)
        setup_webhook()

def run_flask():
    """Запуск Flask приложения"""
    port = int(os.environ.get('PORT', 8080))
    print(f"\n🚀 Запуск Flask на порту {port}")
    print(f"📡 Webhook endpoint: POST /webhook")
    print(f"🏠 Главная страница: http://localhost:{port}")
    print(f"❤️  Health check: http://localhost:{port}/health")
    
    # Отключаем логи Flask для чистоты
    import werkzeug
    werkzeug_log = logging.getLogger('werkzeug')
    werkzeug_log.setLevel(logging.ERROR)
    
    flask_app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False
    )

# ====== ГЛАВНАЯ ФУНКЦИЯ ======
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ЗАПУСК БОТА С WEBHOOK (python-telegram-bot v20)")
    print("=" * 60)
    
    # Проверяем переменные окружения
    print(f"🔍 Проверка окружения:")
    print(f"   PORT: {os.environ.get('PORT', '8080')}")
    print(f"   RENDER: {'Да' if 'RENDER' in os.environ else 'Нет'}")
    print(f"   PYTHON_VERSION: {os.environ.get('PYTHON_VERSION', 'Не установлен')}")
    print(f"   BOT_TOKEN: {'Установлен' if BOT_TOKEN else 'НЕ УСТАНОВЛЕН!'}")
    
    if not BOT_TOKEN:
        sys.exit(1)
    
    # Инициализируем приложение Telegram
    try:
        telegram_app = create_telegram_app()
        
        # Запускаем настройку webhook в отдельном потоке
        webhook_thread = Thread(target=setup_webhook, daemon=True)
        webhook_thread.start()
        
        # Запускаем Flask (блокирующий вызов)
        run_flask()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске: {e}")
        sys.exit(1)
