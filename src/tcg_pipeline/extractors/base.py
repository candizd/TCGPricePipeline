"""Kaynak-değiştirilebilir extractor arayüzü.

CLAUDE.md kuralı: tek bir API'a kilitlenme. Her veri kaynağı (JustTCG,
PokemonPriceTracker, ...) bu Protocol'ü uygular; pipeline somut sınıfa değil
bu arayüze bağımlı kalır.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PriceExtractor(Protocol):
    """Bir fiyat kaynağının uyması gereken minimum sözleşme.

    F1'de doldurulacak; şimdilik şekil belli olsun diye iskelet.
    """

    source_name: str  # ör. "justtcg" — bronze'da kaynak ayrımı için

    def fetch_raw(self, **params: Any) -> list[dict[str, Any]]:
        """Kaynaktan HAM JSON kayıtları döndür (normalize ETME — bronze ham kalır)."""
        ...
