from __future__ import annotations

from datetime import datetime


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def now_filename() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")
