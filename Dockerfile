FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
COPY constraints.txt .

# Установка зависимостей с учётом ограничений
RUN pip install --no-cache-dir -r requirements.txt --constraint constraints.txt

# Копируем весь проект
COPY . .

# Запуск приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
