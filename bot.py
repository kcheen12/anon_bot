#!/usr/bin/env python3
import os
import time
import logging
import sqlite3
import asyncio
from threading import Thread, Event
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Настройка переменных окружения
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8529167671:AAGqhrDUoU8-v3zcqNwPP4mGDT8id5BeZ5I")
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
    format='[%(asctime)s] %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)

# ====== БАЗА ДАННЫХ ======
def init_db():
    """Инициализация базы данных"""
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
    logging.info("База данных инициализирована")

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
    except Exception as e:
        logging.error(f"Ошибка сохранения пользователя {user.id}: {e}")

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
        logging.error(f"Ошибка получения пользователей: {e}")
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
        logging.error(f"Ошибка получения количества пользователей: {e}")
        return 0

# ====== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ======
telegram_app = None
shutdown_event = Event()

# ====== КОМАНДЫ ======
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
            logging.error(f"Не удалось отправить пользователю {user_id}: {e}")
    
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

# ====== ОБРАБОТЧИКИ СООБЩЕНИЙ ======
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений от обычных пользователей"""
    user = update.effective_user
    
    # Сохраняем пользователя в БД
    save_user(user)
    
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
                    logging.info(f"Сохранил связь: {sent_message.message_id} → {user.id}")
                
            except Exception as e:
                logging.error(f"Не удалось отправить админу {admin_id}: {e}")
        
        await msg.reply_text(
            "Сообщение отправлено всем админам, не спамь. "
            "Как получишь ответ - отпишись сообщением, чтобы уведомить остальных >.<"
        )
    
    except Exception as e:
        logging.error(f"Ошибка: {e}")
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
        logging.info(f"Сообщение админа {user.id} не является ответом")
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
            logging.error(f"Ошибка отправки анонеру {target_user_id}: {e}")
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

# ====== ИНИЦИАЛИЗАЦИЯ БОТА ======
def create_telegram_app():
    """Создание и настройка приложения Telegram"""
    print(f"\n{'='*50}")
    print(f"🚀 ИНИЦИАЛИЗАЦИЯ WEBHOOK БОТА - {time.ctime()}")
    print(f"{'='*50}")
    
    # Инициализация базы данных
    init_db()
    
    # Создаем приложение Telegram
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("users", users_command))
    
    # Добавляем обработчики сообщений
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.User(ADMINS),
        handle_user_message
    ))
    application.add_handler(MessageHandler(
        filters.PHOTO & ~filters.User(ADMINS),
        handle_user_message
    ))
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & filters.User(ADMINS),
        handle_admin_reply
    ))
    
    print(f"✅ Бот инициализирован")
    print(f"👑 Админов: {len(ADMINS)}")
    print(f"📊 Пользователей в базе: {get_user_count()}")
    
    return application

# ====== FLASK APP ДЛЯ WEBHOOK ======
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    """Домашняя страница"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Bot</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .status { color: green; font-size: 24px; }
            .info { margin-top: 20px; color: #666; }
        </style>
    </head>
    <body>
        <h1>🤖 Telegram Bot</h1>
        <div class="status">✅ Бот активен и работает</div>
        <div class="info">
            <p>Webhook настроен и готов к приему обновлений</p>
            <p>Пользователей в базе: {}</p>
            <p>Режим: Webhook (без polling)</p>
        </div>
    </body>
    </html>
    '''.format(get_user_count())

@flask_app.route('/health')
def health():
    """Проверка здоровья для Render"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'users_count': get_user_count(),
        'bot': 'webhook',
        'version': '2.0'
    }), 200

@flask_app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
async def webhook():
    """Endpoint для получения обновлений от Telegram"""
    try:
        # Проверяем, инициализировано ли приложение
        if not telegram_app:
            return jsonify({'status': 'error', 'message': 'Bot not initialized'}), 500
        
        # Парсим обновление от Telegram
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        
        # Обрабатываем обновление
        await telegram_app.initialize()
        await telegram_app.process_update(update)
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        logging.error(f"Ошибка обработки webhook: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def setup_webhook():
    """Настройка webhook"""
    global telegram_app
    
    # Даем время Flask запуститься
    time.sleep(3)
    
    # Получаем URL для webhook
    render_external_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    
    if render_external_url:
        # На Render
        webhook_url = f"{render_external_url}/webhook/{BOT_TOKEN}"
    else:
        # Локальная разработка
        port = int(os.environ.get('PORT', 8080))
        webhook_url = f"http://localhost:{port}/webhook/{BOT_TOKEN}"
        print(f"⚠️  Локальный режим: {webhook_url}")
    
    print(f"🌐 Webhook URL: {webhook_url}")
    
    try:
        # Удаляем старый webhook, если есть
        telegram_app.bot.delete_webhook(drop_pending_updates=True)
        time.sleep(1)
        
        # Устанавливаем новый webhook
        telegram_app.bot.set_webhook(
            url=webhook_url,
            max_connections=100,
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )
        
        print("✅ Webhook успешно установлен")
        print(f"📊 Пользователей в базе: {get_user_count()}")
        print(f"👑 Админов: {len(ADMINS)}")
        print(f"🆔 Ваш ID: {YOUR_ID}")
        
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")
        print("🔄 Повторная попытка через 10 секунд...")
        time.sleep(10)
        setup_webhook()

def run_flask():
    """Запуск Flask приложения"""
    port = int(os.environ.get('PORT', 8080))
    print(f"🚀 Запуск Flask на порту {port}")
    
    # Явно указываем host и port
    flask_app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True
    )

# ====== ГЛАВНАЯ ФУНКЦИЯ ======
if __name__ == "__main__":
    print("=" * 60)
    print("🚀 ЗАПУСК БОТА С WEBHOOK (без polling)")
    print("=" * 60)
    
    # Инициализируем приложение Telegram
    telegram_app = create_telegram_app()
    
    # Запускаем настройку webhook в отдельном потоке
    webhook_thread = Thread(target=setup_webhook, daemon=True)
    webhook_thread.start()
    
    # Запускаем Flask (блокирующий вызов)
    run_flask()
