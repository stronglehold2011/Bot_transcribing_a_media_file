# Низкоуровневая логика для расшифровки аудио с помощью Whisper и ffmpeg

import os
import subprocess
import glob
import logging
from deep_translator import GoogleTranslator
import whisper
from telegram import Update
from telegram.ext import ContextTypes
from asyncio import to_thread

logger = logging.getLogger(__name__)
model = whisper.load_model("small", device="cpu")  # можно поменять на medium/large

# Расшифровка одного файла
async def transcribe_file(file_path: str) -> str:
    try:
        result = await to_thread(model.transcribe, file_path)
        text = result["text"]
        lang = result.get("language", "unknown")

        # Автоматический перевод, если язык не русский
        if lang != "ru":
            translated = GoogleTranslator(source='auto', target='ru').translate(text)
            return f"🔤 Обнаружен язык: {lang}\n\nОригинал:\n{text}\n\nПеревод:\n{translated}"
        else:
            return text

    except Exception as e:
        logger.error(f"Ошибка расшифровки файла {file_path}: {e}")
        return "⚠️ Произошла ошибка при распознавании речи."


# Обработка длинных аудио: разбивка + склейка результата
async def transcribe_long_audio(wav_path: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    base = os.path.splitext(os.path.basename(wav_path))[0]
    segment_pattern = os.path.join("temp", f"{base}_segment_%03d.wav")

    try:
        # Разбиваем на 60-секундные куски
        subprocess.run([
            'ffmpeg', '-y', '-i', wav_path, '-f', 'segment', '-segment_time', '60', '-c', 'copy', segment_pattern
        ], check=True)

        segment_files = sorted(glob.glob(os.path.join("temp", f"{base}_segment_*.wav")))
        if not segment_files:
            raise RuntimeError("Сегменты не были созданы.")

        all_texts = []
        msg = None

        if not context.user_data.get("silent_mode"):
            msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⏳ Обработка...")

        for idx, segment in enumerate(segment_files, 1):
            # Обновление прогресса
            if msg:
                progress_bar = "█" * idx + "░" * (len(segment_files) - idx)
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    text=f"⏳ Обработка... [{progress_bar}] ({idx}/{len(segment_files)})"
                )

            segment_text = await transcribe_file(segment)
            all_texts.append(segment_text)
            os.remove(segment)

        if msg:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=msg.message_id,
                text=f"✅ Обработка завершена! [{ '█' * len(segment_files) }] ({len(segment_files)}/{len(segment_files)})"
            )

        return "\n\n".join(all_texts)

    except Exception as e:
        logger.error(f"Ошибка при обработке длинного файла: {e}")
        return "⚠️ Произошла ошибка при обработке длинного файла."