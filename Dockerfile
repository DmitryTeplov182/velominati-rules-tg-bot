# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем пользователя с UID 1000 для корректных прав на файлы
RUN useradd --create-home --shell /bin/bash --uid 1000 botuser \
    && chown -R botuser:botuser /app
USER botuser

# Команда запуска
CMD ["python", "telegram_bot.py"]
