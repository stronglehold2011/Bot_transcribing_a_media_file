# Обработчики пользовательских команд:
# /start, /status, /silence, /nosilence и нажатие кнопки «Начать пользоваться»

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.auth import APPROVED_USERS
from bot.queue_worker import transcription_queue

# Команда /start (и /help) — приветствие
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Проверяем: одобрен ли пользователь
    if user_id in APPROVED_USERS:
        await update.message.reply_text(
            "Привет! Я могу расшифровывать голосовые, аудио, видео и ссылки.\n"
            "Просто отправь сообщение — и я его обработаю.\n\n"
            "Доступные команды:\n"
            "/status — узнать очередь\n"
            "/silence — тихий режим (без лишнего)\n"
            "/nosilence — обычный режим"
        )
    else:
        # Пользователь не одобрен — предлагаем запросить доступ
        keyboard = [[InlineKeyboardButton("Начать пользоваться", callback_data="request_access")]]
        await update.message.reply_text(
            "Привет! Нажми кнопку ниже, чтобы отправить запрос на доступ:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# Команда /status — выводит текущую длину очереди
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    queue_size = transcription_queue.qsize()
    if queue_size >= 100:
        await update.message.reply_text(f"Сейчас в очереди: {queue_size}. Пожалуйста, подождите.")
    else:
        await update.message.reply_text("Очередь пуста или минимальна. Запрос скоро обработается.")


# Команда /silence — тихий режим (в группах)
async def silence_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id

    if chat.type not in ["group", "supergroup", "channel"]:
        await update.message.reply_text("⚠️ Режим тишины работает только в группах и каналах.")
        return

    # Проверяем права
    member = await context.bot.get_chat_member(chat.id, user_id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("⛔ Только администратор может включать режим тишины.")
        return

    context.user_data["silent_mode"] = True
    await update.message.reply_text("🔕 Режим тишины включён. Бот будет отвечать только результатом.")


# Команда /nosilence — отключение тихого режима
async def unsilence_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user_id = update.effective_user.id

    if chat.type not in ["group", "supergroup", "channel"]:
        await update.message.reply_text("⚠️ Эта команда работает только в группах и каналах.")
        return

    member = await context.bot.get_chat_member(chat.id, user_id)
    if member.status not in ("administrator", "creator"):
        await update.message.reply_text("⛔ Только администратор может отключать режим тишины.")
        return

    context.user_data["silent_mode"] = False
    await update.message.reply_text("🔔 Режим тишины отключён. Бот будет уведомлять о ходе обработки.")


# Обработка кнопки «Начать пользоваться»
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "request_access":
        await query.edit_message_text("✅ Запрос отправлен. Ожидайте одобрения от администратора.")

        # Отправляем уведомление админу
        from bot.main import ADMIN_IDS  # можно перенести в settings
        admin_id = list(ADMIN_IDS)[0]

        keyboard = [[
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("🚫 Отклонить", callback_data=f"reject_{user_id}")
        ]]
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🔔 Запрос на доступ: `{user_id}` — *{query.from_user.full_name}*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"Не удалось уведомить администратора: {e}")