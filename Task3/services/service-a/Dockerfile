FROM python:3.12-slim

WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY app.py .

# Открытие порта
EXPOSE 8080

# Запуск приложения
CMD ["python", "app.py"]
