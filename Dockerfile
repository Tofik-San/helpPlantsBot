FROM python:3.11-slim

# 1. Создаём рабочую директорию
WORKDIR /app

# 2. Копируем requirements.txt отдельно
COPY requirements.txt .

# 3. Ставим pip и зависимости — будет кешироваться
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 4. Теперь копируем весь остальной код
COPY . .

# 5. Открываем порт и запускаем приложение
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
