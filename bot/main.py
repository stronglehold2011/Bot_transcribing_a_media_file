# Точка входа в приложение Telegram-бота.
# Здесь инициализируются все обработчики, запускается очередь и сам бот.

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from config.settings import BOT_TOKEN  # Токен берётся из .env
from bot.handlers import admin, user, transcribe
from bot.queue_worker import queue_worker
from bot.services.utils import clean_temp_dir


# Функция, вызываемая при запуске приложения
# Очищает временные файлы и запускает фоновые воркеры
async def post_init(app):
    clean_temp_dir()  # удаляем старые файлы
    for _ in range(3):  # запускаем 3 фоновых воркера
        app.create_task(queue_worker())


def run():
    # Создаём экземпляр Telegram-приложения
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Общие команды для пользователей
    app.add_handler(CommandHandler("start", user.handle_start))
    app.add_handler(CommandHandler("help", user.handle_start))
    app.add_handler(CommandHandler("status", user.status))
    app.add_handler(CommandHandler("silence", user.silence_mode))
    app.add_handler(CommandHandler("nosilence", user.unsilence_mode))

    # Админ-команды
    app.add_handler(CommandHandler("approve", admin.approve_user))
    app.add_handler(CommandHandler("reject", admin.reject_user))
    app.add_handler(CommandHandler("users", admin.list_users))
    app.add_handler(CommandHandler("makeadmin", admin.make_admin_cmd))
    app.add_handler(CommandHandler("revokeadmin", admin.revoke_admin_cmd))

    # Callback-кнопки: одобрение, удаление, список ожидающих
    app.add_handler(CallbackQueryHandler(admin.handle_admin_callback, pattern="^(reject_|approve_|show_pending)"))
    app.add_handler(CallbackQueryHandler(user.handle_callback))  # для кнопки «Начать пользоваться»

    # Обработка входящих медиа-файлов и ссылок
    app.add_handler(MessageHandler(filters.VOICE, transcribe.transcribe_voice))
    app.add_handler(MessageHandler(
        filters.AUDIO | filters.VIDEO | filters.Document.ALL | filters.VIDEO_NOTE,
        transcribe.transcribe_media
    ))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), transcribe.transcribe_from_link))

    # Запуск бота (polling)
    app.run_polling()


# Точка входа в Python-приложение
if __name__ == "__main__":
    run()