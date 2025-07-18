import os
from datetime import datetime
import asyncpg
from urllib.parse import urlparse

# --- Разбор DATABASE_URL из .env
DATABASE_URL = os.getenv("DATABASE_URL")
parsed = urlparse(DATABASE_URL) if DATABASE_URL else None

PG_USER = parsed.username if parsed else None
PG_PASSWORD = parsed.password if parsed else None
PG_HOST = parsed.hostname if parsed else None
PG_PORT = parsed.port if parsed else None
PG_DB = parsed.path[1:] if parsed and parsed.path.startswith('/') else None

_pool = None

async def get_pool():
    """Вернуть кешированный пул соединений с PostgreSQL"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DB,
        )
    return _pool

async def check_and_increment_limit(user_id: int) -> bool:
    """
    Проверить и обновить лимит. Возвращает True — если можно, False — если лимит исчерпан.
    Лимит: 3 запроса в сутки на одного user_id.
    """
    pool = await get_pool()
    today = datetime.utcnow().date()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT count FROM photo_usage WHERE user_id = $1 AND date = $2",
            user_id, today
        )

        if row:
            if row["count"] >= 3:
                return False
            await conn.execute(
                "UPDATE photo_usage SET count = count + 1 WHERE user_id = $1 AND date = $2",
                user_id, today
            )
        else:
            await conn.execute(
                "INSERT INTO photo_usage (user_id, date, count) VALUES ($1, $2, 1)",
                user_id, today
            )

    return True
