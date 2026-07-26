from datetime import datetime


def now() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")
