from datetime import datetime, date, timedelta

# In-memory storage for usage data
_photo_usage = {}


def _get_info(user_id: int):
    """Retrieve or initialize user info, resetting daily limits if needed."""
    today = date.today()
    info = _photo_usage.get(user_id)
    if info is None or info['date'] != today:
        # Initialize or reset for new day
        info = {'count': 0, 'last_time': datetime.min, 'date': today}
        _photo_usage[user_id] = info
    return info


def check_photo_limit(user_id: int) -> bool:
    """Return True if the user has remaining daily photo recognitions."""
    info = _get_info(user_id)
    return info['count'] < 3


def check_rate_limit(user_id: int) -> bool:
    """Return True if at least 15 seconds passed since the user's last photo."""
    info = _get_info(user_id)
    now = datetime.now()
    return now - info['last_time'] >= timedelta(seconds=15)


def register_photo_usage(user_id: int):
    """Register a successful photo recognition for the user."""
    info = _get_info(user_id)
    info['last_time'] = datetime.now()
    info['count'] += 1
