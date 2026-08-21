from datetime import datetime


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def safe_float(value, default=None):
    if value in (None, ""):
        return default
    return float(value)


def safe_int(value, default=None):
    if value in (None, ""):
        return default
    return int(value)
