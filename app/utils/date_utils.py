from datetime import datetime, timedelta, timezone

# Indian Standard Time is UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30))

def get_ist_now():
    """Returns the current datetime in IST."""
    return datetime.now(IST)

def get_ist_today_range():
    """
    Returns (start, end) of the current day in IST.
    start: 00:00:00 of today (IST)
    end: 00:00:00 of tomorrow (IST)
    """
    now = get_ist_now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end
