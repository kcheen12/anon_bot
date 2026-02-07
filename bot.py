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
    msg = update.message

    if msg.text and msg.text.startswith('/'):
        return

    try:
        for admin_id in ADMINS:
            try:
                if msg.photo:
                    await context.bot.send_photo(
                        chat_id=admin_id,
                        photo=msg.photo[-1].file_id,
                        caption=f"👤 Пользователь: {user.id}\n\n"
                                f"📷 Фото\n"
                                f"{msg.caption if msg.caption else ''}\n\n"
                                f"🕒 {msg.date.strftime('%H:%M')}",
                        parse_mode="Markdown"
                    )
                    
                elif msg.text:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"👤 Пользователь: {user.id}\n\n"
                             f"💬 {msg.text}\n\n"
                             f"🕒 {msg.date.strftime('%H:%M')}",
                        parse_mode="Markdown"
                    )
                
                else:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"👤 Пользователь: {user.id}\n\n"
                             f"📎 Файл/Медиа\n\n"
                             f"🕒 {msg.date.strftime('%H:%M')}",
                        parse_mode="Markdown"
                    )

                print(f"📤 [{user.id}] → Админу {admin_id}")

            except Exception as e:
                print(f"Не удалось отправить админу {admin_id}: {e}")

        await msg.reply_text("Сообщение отправлено всем админам, советую не спамить и дождаться ответа одного из.")

    except Exception as e:
        print(f"Ошибка: {e}")
        await msg.reply_text("Ошибка, попробуй позже")

# ОТВЕТЫ ОТ АДМИНОВ
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    if user.id not in ADMINS:
        return

    if msg.text and msg.text.startswith('/'):
        return

    if msg.reply_to_message:
        replied_text = msg.reply_to_message.text or msg.reply_to_message.caption
        
        if replied_text and "Пользователь:" in replied_text:
            try:
                lines = replied_text.split('\n')
                user_line = lines[0]
                target_user_id = int(user_line.replace("👤 Пользователь:", "").strip())
                
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"💌 *Ответ от администратора:*\n\n{msg.text}",
                    parse_mode="Markdown"
                )

                await msg.reply_text(f"✅ Ответ отправлен пользователю {target_user_id}")

                for admin_id in ADMINS:
                    if admin_id != user.id:
                        try:
                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=f"👤 Админ ответил пользователю {target_user_id}"
                            )
                        except:
                            pass

                print(f"📨 Админ {user.id} → Пользователю {target_user_id}")
                return

            except Exception as e:
                print(f"Ошибка: {e}")
                await msg.reply_text("❌ Ошибка")
                return
    
    await msg.reply_text(
        "📌 *Как ответить пользователю:*\n\n"
        "1. Найдите сообщение от бота с текстом 'Пользователь:'\n"
        "2. Нажмите 'Ответить' на него\n"
        "3. Напишите текст\n\n"
        "Бот отправит ответ анонимно.",
        parse_mode="Markdown"
    )

# ЗАПУСК БОТА (ВСЁ ИСПРАВЛЕНО ЗДЕСЬ!)
if __name__ == "__main__":
    print(f"👑 Администраторы ({len(ADMINS)}):")
    for i, admin_id in enumerate(ADMINS, 1):
        print(f"  {i}. ID: {admin_id}")
    
    # СОЗДАЁМ БОТА
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ДОБАВЛЯЕМ ОБРАБОТЧИКИ
    app.add_handler(CommandHandler("start", start))
    
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_user_message
    ))
    
    app.add_handler(MessageHandler(
        filters.PHOTO,
        handle_user_message
    ))
    
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(ADMINS),
        handle_admin_reply
    ))
    
    print("\n✅ Бот запущен!")
    print("=" * 50)
    
    # ЗАПУСКАЕМ БОТА (ОДИН РАЗ!)
    app.run_polling()
