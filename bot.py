#!/usr/bin/env python3""
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8529167671:AAGqhrDUoU8-v3zcqNwPP4mGDT8id5BeZ5I"
ADMINS = [
    7976904182, #я
    5410696822,  # лиза
    7032286132,  # жан
    7607540379,  # нари
    6806766903, #тсунэтами
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
    logging.info(f"Доступные ключи в forward_map: {list(forward_map.keys())}")

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

            await msg.reply_text(f"Ответ отправлен анонеру")
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


def main():
    print(f"👑 Администраторы ({len(ADMINS)}):")
    for i, admin_id in enumerate(ADMINS, 1):
        print(f"  {i}. ID: {admin_id}")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.User(ADMINS),
        handle_user_message
    ))

    app.add_handler(MessageHandler(
        filters.PHOTO & ~filters.User(ADMINS),
        handle_user_message
    ))

    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & filters.User(ADMINS),
        handle_admin_reply
    ))

    app.run_polling()


if __name__ == "__main__":
    main()

