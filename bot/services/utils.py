# Утилиты: очистка временной папки и другие вспомогательные функции

import os
import time
import logging

logger = logging.getLogger(__name__)

TEMP_DIR = "temp"  # Папка для временных файлов

# Очистка временной папки от старых файлов (старше 1 часа)
def clean_temp_dir():
    now = time.time()

    for file in os.listdir(TEMP_DIR):
        full_path = os.path.join(TEMP_DIR, file)

        if os.path.isfile(full_path):
            age = now - os.path.getmtime(full_path)
            if age > 3600:  # 1 час
                try:
                    os.remove(full_path)
                    logger.info(f"Удалён устаревший файл: {full_path}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить файл {full_path}: {e}")