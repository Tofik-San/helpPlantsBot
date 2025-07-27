FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NIXPACKS_PATH=/opt/venv/bin:$NIXPACKS_PATH

WORKDIR /app

# Сначала копируем весь проект
COPY . .

# Кеш pip
RUN --mount=type=cache,id=s/pip,target=/root/.cache/pip \
    python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

CMD ["python", "main.py"]
