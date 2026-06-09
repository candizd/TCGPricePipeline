"""JustTCG extractor — ana kaynak (One Piece + Pokémon, JP/EN).

F1 keşif aşaması: auth + rate limit (429 backoff) + ham çekim.
Free tier: 1000 istek/ay · 100/gün · 10/dk. Bu yüzden batch (POST /cards, ≤200)
ve dikkatli istek sayımı kritik.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from tcg_pipeline import config

BASE_URL = "https://api.justtcg.com/v1"
SOURCE_NAME = "justtcg"


class JustTCGError(RuntimeError):
    pass


class JustTCGExtractor:
    """PriceExtractor protokolünü uygular (base.PriceExtractor)."""

    source_name = SOURCE_NAME

    def __init__(self, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.api_key = api_key or config.get("JUSTTCG_API_KEY")
        if not self.api_key:
            raise JustTCGError("JUSTTCG_API_KEY yok — .env'e ekle.")
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers={"x-api-key": self.api_key},
            timeout=timeout,
        )

    # --- düşük seviye: 429 backoff'lu GET ---
    def _get(self, path: str, params: dict[str, Any] | None = None, *, max_retries: int = 5) -> dict:
        delay = 1.0
        for attempt in range(max_retries + 1):
            resp = self._client.get(path, params=params)
            if resp.status_code == 429:
                # rate limit — Retry-After'ı onurlandır, yoksa exp backoff + cap 30s
                wait = float(resp.headers.get("Retry-After", delay))
                if attempt == max_retries:
                    raise JustTCGError(f"429: {max_retries} denemede geçilemedi ({path})")
                time.sleep(min(wait, 30.0))
                delay = min(delay * 2, 30.0)
                continue
            resp.raise_for_status()
            return resp.json()
        raise JustTCGError("ulaşılamaz")  # mantıken buraya gelinmez

    # --- keşif yardımcıları (F1) ---
    def list_games(self) -> dict:
        return self._get("/games")

    def list_sets(self, game: str) -> dict:
        return self._get("/sets", params={"game": game})

    def get_cards(self, **params: Any) -> dict:
        """Ham /cards yanıtı. params: game, set, q, limit, orderBy, ..."""
        return self._get("/cards", params=params)

    # --- Protocol arayüzü ---
    def fetch_raw(self, **params: Any) -> list[dict[str, Any]]:
        """Ham kart kayıtları (bronze'a yazılacak — normalize ETME)."""
        data = self.get_cards(**params)
        return data.get("data", data) if isinstance(data, dict) else data

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> JustTCGExtractor:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
