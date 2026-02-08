#!/usr/bin/env python3
import logging
import time
import traceback
import asyncio
import sys
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8529167671:AAGqhrDUoU8-v3zcqNwPP4mGDT8id5BeZ5I"
ADMINS = [
    7976904182, #я
    5410696822,  # лиза
    7032286132,  # жан
    7607540379,  # нари
]

forward_map = {}

logging.basicConfig(
    format='[%(asctime)s] %(message)s',
    level=logging.INFO,
    datefmt='%H:%M:%S'
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*KEEP IT QUIET*\n\n"
        "Бот для проверки возраста.\n"
        "Возрастное ограничение составляет 15+. Отправь фото любого документа, подтверждающего возраст (нужна только дата рождения, не более). Также на фото должна быть бумажка с вашим ником. Данные не выходят за рамки чата, не используются в личных целях.\n\n"
        "По тех вопросам/неполадкам: @SexPriest",
        parse_mode="Markdown"
    )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

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
                        caption=f"*Анонер {user.id}*\n\n"
                                f"{msg.caption if msg.caption else ''}\n\n",
                        parse_mode="Markdown"
                    )

                elif msg.text:
                    sent_message = await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"*Анонер {user.id}*\n\n"
                             f"{msg.text}\n\n",
                        parse_mode="Markdown"
                    )

                else:
                    sent_message = await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"*Анонер {user.id}*\n\n"
                             f"Файл/Медиа\n\n",
                        parse_mode="Markdown"
                    )

                # Сохраняем связь между сообщением админа и пользователя
                if sent_message:
                    forward_map[sent_message.message_id] = (user.id, msg.message_id)
                    logging.info(
                        f"Сохранил связь: сообщение {sent_message.message_id} → пользователь {user.id}, msg_id {msg.message_id}")

                logging.info(f"[{user.id}] → Админу {admin_id}")

            except Exception as e:
                logging.error(f"Не удалось отправить админу {admin_id}: {e}")

        await msg.reply_text("Сообщение отправлено всем админам, не спамь. Как получишь ответ - отпишись сообщением, чтобы уведомить остальных >.<")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await msg.reply_text("Ошибка, попробуй позже")


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    # Проверяем, что это админ
    if user.id not in ADMINS:
        return

    # Пропускаем команды
    if msg.text and msg.text.startswith('/'):
        return

    # Проверяем, является ли сообщение ответом на что-либо
    if not msg.reply_to_message:
        logging.info(f"Сообщение админа {user.id} не является ответом")
        return

    replied_msg_id = msg.reply_to_message.message_id

    logging.info(f"Админ {user.id} ответил на сообщение {replied_msg_id}")

    # Проверяем, есть ли это сообщение в нашем словаре
    if replied_msg_id in forward_map:
        target_user_id, target_message_id = forward_map[replied_msg_id]

        logging.info(
            f"Нашел связь: сообщение {replied_msg_id} → пользователь {target_user_id}, msg_id {target_message_id}")

        try:
            # Отправляем ответ пользователю, отвечая на его исходное сообщение
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
                # Для других типов сообщений (документы, стикеры и т.д.)
                await context.bot.copy_message(
                    chat_id=target_user_id,
                    from_chat_id=msg.chat_id,
                    message_id=msg.message_id,
                    reply_to_message_id=target_message_id
                )

            await msg.reply_text(f"✅ Ответ отправлен анонеру")
            logging.info(f"📨 Админ {user.id} → Пользователю {target_user_id} (ответ на msg {target_message_id})")

        except Exception as e:
            logging.error(f"Ошибка отправки анонеру {target_user_id}: {e}")
            await msg.reply_text(f"❌ Не удалось отправить пользователю: {e}")

    else:
        logging.warning(f"Сообщение {replied_msg_id} не найдено в forward_map")
        await msg.reply_text(
            "Это сообщение не является пересланным от пользователя или устарело.\n\n"
            "📌 *Как ответить пользователю:*\n"
            "1. Найдите сообщение от бота с текстом 'Пользователь:'\n"
            "2. Нажмите 'Ответить' на него\n"
            "3. Напишите текст\n\n"
            "Бот отправит ответ анонимно.",
            parse_mode="Markdown"
        )


def run_flask():
    """Запуск Flask сервера для Render"""
    app = Flask(__name__)
    
    @app.route('/')
    def home():
        return '🤖 Telegram Bot is running', 200
    
    @app.route('/health')
    def health():
        return 'OK', 200
    
    port = 8080
    print(f"🌐 Flask запущен на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


async def run_bot_async():
    """Асинхронная функция запуска бота"""
    print(f"\n{'='*50}")
    print(f"🚀 ЗАПУСК БОТА - {time.ctime()}")
    print(f"{'='*50}")
    
    print(f"👑 Администраторы ({len(ADMINS)}):")
    for i, admin_id in enumerate(ADMINS, 1):
        print(f"  {i}. ID: {admin_id}")

    # Создаем приложение
    app = Application.builder() \
        .token(BOT_TOKEN) \
        .concurrent_updates(True) \
        .build()

    app.add_handler(CommandHandler("start", start))
    
    # Фильтр для обычных пользователей (не админов)
    user_filter = ~filters.User(user_id=ADMINS)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & user_filter,
        handle_user_message
    ))
    app.add_handler(MessageHandler(
        filters.PHOTO & user_filter,
        handle_user_message
    ))
    
    # Фильтр для админов
    admin_filter = filters.User(user_id=ADMINS) & ~filters.COMMAND
    app.add_handler(MessageHandler(
        admin_filter,
        handle_admin_reply
    ))

    print("✅ Бот запущен")
    
    # Запускаем polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        drop_pending_updates=True,
        poll_interval=1.0,
        timeout=10,
        bootstrap_retries=-1,
        read_timeout=10,
        write_timeout=10,
        connect_timeout=10,
        pool_timeout=10
    )
    
    # Ждем пока бот работает
    await asyncio.Event().wait()


def run_bot():
    """Запуск бота"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_bot_async())
    except KeyboardInterrupt:
        print("\n👋 Остановка бота")
    except Exception as e:
        raise e
    finally:
        loop = asyncio.get_event_loop()
        if not loop.is_closed():
            loop.close()


if __name__ == "__main__":
    # Запускаем Flask в отдельном потоке
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Ждем немного чтобы Flask запустился
    time.sleep(2)
    
    # БЕСКОНЕЧНЫЙ ЦИКЛ ПЕРЕЗАПУСКА
    restart_count = 0
    max_restarts = 50
    
    while restart_count < max_restarts:
        try:
            run_bot()
            break
        except KeyboardInterrupt:
            print("\n👋 Остановка бота по команде пользователя")
            break
        except Exception as e:
            restart_count += 1
            print(f"\n{'='*50}")
            print(f"💥 БОТ УПАЛ (перезапуск #{restart_count}/{max_restarts})")
            print(f"Ошибка: {e}")
            traceback.print_exc()
            print(f"{'='*50}")
            
            # Ждем перед перезапуском
            wait_time = min(30, 10 * restart_count)  # от 10 до 30 секунд
            print(f"🔄 Перезапуск через {wait_time} секунд...")
            time.sleep(wait_time)
    
    if restart_count >= max_restarts:
        print(f"\n❌ Достигнут максимум перезапусков ({max_restarts}). Бот остановлен.")
