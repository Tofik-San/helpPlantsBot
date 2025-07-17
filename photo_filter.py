import os
import logging
import base64
import imghdr
from collections import defaultdict
from typing import Optional, Dict

from PIL import Image  # BLOCK 1: pillow used for dimension check
import aiohttp

PLANT_ID_API_KEY = os.getenv("PLANT_ID_API_KEY")
HEADERS = {
    "Content-Type": "application/json",
    "Api-Key": PLANT_ID_API_KEY,
}

logger = logging.getLogger(__name__)

# Track consecutive failures per user for soft warnings
_failures: Dict[int, int] = defaultdict(int)


# BLOCK 1: встроена валидация, лимиты не горят
async def filter_and_identify(image_path: str, user_id: int) -> Optional[dict]:
    """Validate image and recognize plant via Plant.id."""
    # Check image format
    img_type = imghdr.what(image_path)
    if img_type not in {"jpeg", "png"}:
        logger.info(f"[BLOCK1] {user_id}: unsupported format {img_type}")
        _failures[user_id] += 1
        if _failures[user_id] >= 3:
            logger.info(f"[BLOCK1] {user_id}: three failed attempts")
        return None

    # Check file size
    if os.path.getsize(image_path) > 5 * 1024 * 1024:
        logger.info(f"[BLOCK1] {user_id}: file too large")
        _failures[user_id] += 1
        if _failures[user_id] >= 3:
            logger.info(f"[BLOCK1] {user_id}: three failed attempts")
        return None

    # Check proportions
    try:
        with Image.open(image_path) as img:
            width, height = img.size
        ratio = max(width, height) / min(width, height)
        if ratio > 3:
            logger.info(f"[BLOCK1] {user_id}: bad proportions {width}x{height}")
            _failures[user_id] += 1
            if _failures[user_id] >= 3:
                logger.info(f"[BLOCK1] {user_id}: three failed attempts")
            return None
    except Exception as e:
        logger.error(f"[BLOCK1] {user_id}: error reading image - {e}")
        _failures[user_id] += 1
        if _failures[user_id] >= 3:
            logger.info(f"[BLOCK1] {user_id}: three failed attempts")
        return None

    # Read and encode image
    try:
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"[BLOCK1] {user_id}: file read error - {e}")
        return None

    payload = {"images": [image_b64], "organs": ["leaf", "flower"]}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.plant.id/v2/identify", headers=HEADERS, json=payload
            ) as resp:
                if resp.status != 200:
                    logger.error(
                        f"[BLOCK1] {user_id}: Plant.id status {resp.status}"
                    )
                    _failures[user_id] += 1
                    if _failures[user_id] >= 3:
                        logger.info(
                            f"[BLOCK1] {user_id}: three failed attempts"
                        )
                    return None
                result = await resp.json()
    except Exception as e:
        logger.error(f"[BLOCK1] {user_id}: request error - {e}")
        return None

    if result.get("is_plant_probability", 0) < 0.2:
        logger.info(f"[BLOCK1] {user_id}: low is_plant_probability")
        _failures[user_id] += 1
        if _failures[user_id] >= 3:
            logger.info(f"[BLOCK1] {user_id}: three failed attempts")
        return None

    suggestions = result.get("suggestions")
    if not suggestions:
        logger.info(f"[BLOCK1] {user_id}: no suggestions")
        _failures[user_id] += 1
        if _failures[user_id] >= 3:
            logger.info(f"[BLOCK1] {user_id}: three failed attempts")
        return None

    top = suggestions[0]
    _failures[user_id] = 0  # reset on success
    return {
        "latin_name": top.get("plant_name", ""),
        "confidence": top.get("probability", 0),
    }
