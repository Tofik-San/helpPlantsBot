from limits.rate_limit import (
    check_photo_limit,
    check_rate_limit,
    register_photo_usage,
)
from photo_filter import filter_and_identify


# BLOCK 1:
async def handle_photo(user_id: int, image_path: str) -> str:
    """Process uploaded photo and return recognition result message."""
    if not check_photo_limit(user_id):
        return "❌ Лимит распознаваний на сегодня исчерпан."
    if not check_rate_limit(user_id):
        return "⌛ Подождите немного перед следующим распознаванием."

    result = await filter_and_identify(image_path, user_id)

    if result is None:
        return "❌ Не удалось распознать растение. Попробуйте другое фото."

    register_photo_usage(user_id)
    return f"✅ Фото принято: {result['latin_name']} ({result['confidence']:.0%})"
