# Обработка голосовых, аудио, видеофайлов и ссылок
# Очередь, ffmpeg-конвертация, Whisper, перевод

import os
import uuid
import subprocess
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from bot.auth import check_access
from bot.queue_worker import transcription_queue

# Голосовые сообщения (.ogg)
async def transcribe_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update, context):
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    uid = f"{voice.file_unique_id}_{uuid.uuid4().hex[:8]}"
    temp_dir = "temp"

    input_path = os.path.join(temp_dir, f"{uid}.ogg")
    wav_path = os.path.join(temp_dir, f"{uid}.wav")

    msg = await update.message.reply_text("⏳ Скачиваю голосовое...")

    try:
        await file.download_to_drive(input_path)

        await context.bot.edit_message_text(chat_id=msg.chat_id, message_id=msg.message_id, text="⏳ Конвертирую...")

        # Конвертация с фильтрацией
        subprocess.run([
            'ffmpeg', '-y', '-i', input_path,
            '-ar', '16000', '-ac', '1',
            '-af', 'highpass=f=200, lowpass=f=3000, anlmdn',
            wav_path
        ], check=True)

        await context.bot.edit_message_text(chat_id=msg.chat_id, message_id=msg.message_id,
                                            text="⏳ Добавлено в очередь. Ожидайте результат.")
        await transcription_queue.put((wav_path, update, context))

    except Exception as e:
        await context.bot.edit_message_text(chat_id=msg.chat_id, message_id=msg.message_id,
                                            text="⚠️ Ошибка при обработке голосового сообщения.")
        print(f"Ошибка: {e}")
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

# Обработка медиафайлов (аудио, видео, документы)
async def transcribe_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update, context):
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Определяем тип файла и его имя
    message = update.message
    file_info = message.audio or message.video_note or message.video or message.document
    if not file_info:
        return

    uid = uuid.uuid4().hex[:8]
    temp_dir = "temp"

    ext = ".mp4" if hasattr(file_info, 'mime_type') and 'video' in file_info.mime_type else ".wav"
    raw_path = os.path.join(temp_dir, f"raw_{uid}{ext}")
    wav_path = os.path.join(temp_dir, f"converted_{uid}.wav")

    msg = await update.message.reply_text("⏳ Получаю файл...")

    try:
        file = await context.bot.get_file(file_info.file_id)
        await file.download_to_drive(raw_path)

        await context.bot.edit_message_text(chat_id=msg.chat_id, message_id=msg.message_id, text="⏳ Конвертирую...")

        # Конвертируем с фильтрами для Whisper
        subprocess.run([
            'ffmpeg', '-y', '-i', raw_path,
            '-ar', '16000', '-ac', '1',
            '-af', 'highpass=f=200, lowpass=f=3000, anlmdn',
            wav_path
        ], check=True)

        await context.bot.edit_message_text(chat_id=msg.chat_id, message_id=msg.message_id,
                                            text="⏳ Файл добавлен в очередь.")
        await transcription_queue.put((wav_path, update, context))

    except Exception as e:
        await context.bot.edit_message_text(chat_id=msg.chat_id, message_id=msg.message_id,
                                            text="⚠️ Ошибка при обработке файла.")
        print(f"Ошибка: {e}")
    finally:
        if os.path.exists(raw_path):
            os.remove(raw_path)


# Обработка сообщений со ссылками (например, YouTube)
async def transcribe_from_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update, context):
        return

    url = update.message.text.strip()
    if not url.startswith("http"):
        return

    uid = uuid.uuid4().hex[:8]
    temp_dir = "temp"
    mp3_path = os.path.join(temp_dir, f"yt_{uid}.mp3")
    wav_path = os.path.join(temp_dir, f"yt_{uid}.wav")
    msg = await update.message.reply_text("⏳ Скачиваю аудио по ссылке...")

    try:
        import yt_dlp

        # Настройки загрузки
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': mp3_path,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }

        # Скачивание через yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        await context.bot.edit_message_text(chat_id=msg.chat_id, message_id=msg.message_id, text="⏳ Конвертирую...")

        # Конвертация с фильтрацией
        subprocess.run([
            'ffmpeg', '-y', '-i', mp3_path,
            '-ar', '16000', '-ac', '1',
            '-af', 'highpass=f=200, lowpass=f=3000, anlmdn',
            wav_path
        ], check=True)

        await context.bot.edit_message_text(chat_id=msg.chat_id, message_id=msg.message_id,
                                            text="⏳ Аудио добавлено в очередь.")
        await transcription_queue.put((wav_path, update, context))

    except Exception as e:
        await context.bot.edit_message_text(chat_id=msg.chat_id, message_id=msg.message_id,
                                            text="⚠️ Ошибка при скачивании или конвертации.")
        print(f"Ошибка: {e}")
    finally:
        if os.path.exists(mp3_path):
            os.remove(mp3_path)