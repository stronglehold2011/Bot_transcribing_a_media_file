# Модуль фоновой обработки очереди задач на транскрибацию

import os
import logging
from asyncio import Queue
from bot.services.transcription import transcribe_long_audio

# Настройка логгера
logger = logging.getLogger(__name__)

# Глобальная очередь задач
transcription_queue = Queue()


# Асинхронный воркер, который работает с очередью:
# забирает элемент, обрабатывает, отправляет результат и очищает
async def queue_worker():
    while True:
        # Получаем следующую задачу из очереди
        wav_path, update, context = await transcription_queue.get()

        try:
            # Выполняем транскрибацию длинного аудио
            text = await transcribe_long_audio(wav_path, update, context)

            # Отправляем результат частями, если текст длинный
            for i in range(0, len(text), 4000):
                await context.bot.send_message(chat_id=update.effective_chat.id, text=text[i:i+4000])

            await context.bot.send_message(chat_id=update.effective_chat.id, text="✅ Готово")

        except Exception as e:
            # Логируем и уведомляем об ошибке
            logger.error(f"Ошибка при обработке из очереди: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Произошла ошибка при обработке запроса.")

        finally:
            # Удаляем временный файл
            if os.path.exists(wav_path):
                os.remove(wav_path)

            # Уведомляем очередь, что задача завершена
            transcription_queue.task_done()