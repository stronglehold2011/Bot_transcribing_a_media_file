# Обработчики команд администраторов: approve, reject, users и др.

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.models import (
    approve_user_db, reject_user_db,
    get_all_users, make_admin, revoke_admin,
    get_pending_users
)
from bot.auth import is_admin, update_approved_users
from db.models import load_approved_users_db


# Команда /approve <user_id>
async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только администратор может одобрять пользователей.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❗ Используй: /approve <user_id>")
        return

    try:
        target_id = int(context.args[0])
        user_info = await context.bot.get_chat(target_id)
        approve_user_db(target_id, user_info.full_name)
        approved = load_approved_users_db()
        update_approved_users(set(map(int, approved.keys())))
        await update.message.reply_text(f"✅ Пользователь {target_id} одобрен.")
        await context.bot.send_message(chat_id=target_id, text="✅ Ваша заявка одобрена. Можете пользоваться ботом!")
    except Exception:
        await update.message.reply_text("⛔ Неверный user_id или ошибка при одобрении.")


# Команда /reject <user_id>
async def reject_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только администратор может удалять пользователей.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("❗ Используй: /reject <user_id>")
        return

    try:
        target_id = int(context.args[0])
        reject_user_db(target_id)
        approved = load_approved_users_db()
        update_approved_users(set(map(int, approved.keys())))
        await update.message.reply_text(f"🚫 Пользователь {target_id} удалён.")
    except Exception:
        await update.message.reply_text("⛔ Неверный user_id или ошибка при удалении.")


# Команда /users
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только администратор может просматривать пользователей.")
        return

    users = get_all_users()
    if not users:
        await update.message.reply_text("📭 Список одобренных пользователей пуст.")
        return

    for row in users:
        uid = row['id']
        name = row.get('name', 'неизвестно')
        approved_at = row.get('approved_at', '-')
        is_admin_flag = row.get('is_admin', False)
        admin_badge = "🛡️" if is_admin_flag else ""

        keyboard = [[InlineKeyboardButton("Удалить", callback_data=f"reject_{uid}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"{admin_badge} 👤 `{uid}` — *{name}*\n📅 Одобрен: {approved_at}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    # Кнопка показать ожидающих пользователей
    pending_button = [[InlineKeyboardButton("📥 Ожидающие пользователи", callback_data="show_pending")]]
    await update.message.reply_text(
        "📂 Нажми кнопку ниже, чтобы посмотреть список пользователей, ожидающих одобрения:",
        reply_markup=InlineKeyboardMarkup(pending_button)
    )


# Команды управления админами
async def make_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только администратор может назначать других админов.")
        return
    try:
        target_id = int(context.args[0])
        make_admin(target_id)
        await update.message.reply_text(f"✅ Пользователь {target_id} назначен админом.")
    except Exception:
        await update.message.reply_text("⛔ Ошибка при назначении администратора.")


async def revoke_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Только администратор может снимать админов.")
        return
    try:
        target_id = int(context.args[0])
        revoke_admin(target_id)
        await update.message.reply_text(f"🚫 Пользователь {target_id} больше не админ.")
    except Exception:
        await update.message.reply_text("⛔ Ошибка при удалении администратора.")


# Callback кнопки (approve / reject)
async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not is_admin(user_id):
        await query.edit_message_text("⛔ Доступ запрещён.")
        return

    data = query.data
    if data.startswith("reject_"):
        target_id = int(data.split("_")[1])
        reject_user_db(target_id)

    elif data.startswith("approve_"):
        target_id = int(data.split("_")[1])
        user_info = await context.bot.get_chat(target_id)
        approve_user_db(target_id, user_info.full_name)
        await context.bot.send_message(chat_id=target_id, text="✅ Ваша заявка одобрена. Можете пользоваться ботом!")

    approved = load_approved_users_db()
    update_approved_users(set(map(int, approved.keys())))
    await query.edit_message_text("✅ Выполнено.")

    if data == "show_pending":
        pending = get_pending_users()
        if not pending:
            await query.edit_message_text("📭 Нет ожидающих пользователей.")
            return

        await query.edit_message_text("📋 Список ожидающих:")
        for row in pending:
            uid = row["id"]
            name = row.get("name", "неизвестно")
            keyboard = [[
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{uid}"),
                InlineKeyboardButton("🚫 Отклонить", callback_data=f"reject_{uid}")
            ]]
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"📥 Ожидает: `{uid}` — *{name}*",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )