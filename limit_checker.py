# BLOCK 2: daily limit checker for Plant.id recognitions
import os
from datetime import datetime
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL)
    return _pool

async def check_and_increment_limit(user_id: str) -> bool:
    """Check and update daily recognition limit.

    Returns True if user can perform recognition.
    Increments counter when allowed. Returns False if limit reached.
    """
    pool = await get_pool()
    today = datetime.utcnow().date()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT count FROM photo_usage WHERE user_id=$1 AND date=$2",
            user_id,
            today,
        )
        if row:
            if row["count"] >= 3:
                return False
            await conn.execute(
                "UPDATE photo_usage SET count = count + 1 WHERE user_id=$1 AND date=$2",
                user_id,
                today,
            )
        else:
            await conn.execute(
                "INSERT INTO photo_usage (user_id, date, count) VALUES ($1, $2, 1)",
                user_id,
                today,
            )
    return True
