FROM python:3.11-slim

WORKDIR /app

# Установка системных пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements сначала — чтобы кешировать pip install
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Кешируем модель SentenceTransformer при сборке
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')"

# Копируем всё остальное
COPY . .

CMD ["python", "main.py"]
