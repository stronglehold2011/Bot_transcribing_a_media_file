# Модуль проверки доступа и прав пользователя

from db.models import is_admin as db_is_admin
from telegram import Update
from telegram.ext import ContextTypes

# Глобальный список одобренных пользователей
APPROVED_USERS = set()


# Обновление списка одобренных пользователей (вызывается при запуске)
def update_approved_users(users: set):
    global APPROVED_USERS
    APPROVED_USERS = users


# Проверка: есть ли у пользователя доступ к функционалу бота
async def check_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in APPROVED_USERS:
        await update.message.reply_text("⛔ У вас нет доступа. Ожидайте подтверждения от администратора.")
        return False
    return True


# Проверка: является ли пользователь администратором
def is_admin(user_id: int) -> bool:
    return db_is_admin(user_id)