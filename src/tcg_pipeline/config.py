"""Merkezi config: .env'den okur, kod içinde sabit anahtar yok."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache
def get(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)
