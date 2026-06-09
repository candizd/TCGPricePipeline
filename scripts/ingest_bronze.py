"""F2 ingest: watchlist'teki AKTİF setleri JustTCG'den çekip bronze'a yazar.

Her set -> sayfa sayfa ham JSON -> MinIO bronze. Idempotent (aynı gün tekrar
çalışırsa aynı key'lere yazar). F3'te bu mantık Airflow DAG'ine taşınacak.

Çalıştır:  uv run python scripts/ingest_bronze.py
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from tcg_pipeline.extractors.justtcg import JustTCGExtractor
from tcg_pipeline.storage.bronze import BronzeStore

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

WATCHLIST = Path("config/watchlist.json")


def load_active_sets() -> tuple[list[tuple[str, str, str, dict]], dict]:
    """(source, game, set_id, query_params) listesi + defaults. Sadece enabled."""
    wl = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    defaults = wl.get("defaults", {})
    out: list[tuple[str, str, str, dict]] = []
    for source, games in wl.items():
        if source.startswith("_") or source == "defaults":
            continue
        for game, entries in games.items():
            for e in entries:
                if not e.get("enabled"):
                    continue
                params = {}
                min_price = e.get("min_price", defaults.get("min_price"))
                if min_price is not None:
                    params["min_price"] = min_price
                out.append((source, game, e["set"], params))
    return out, defaults


def main() -> None:
    ingest_date = datetime.now(UTC).strftime("%Y-%m-%d")
    active, _ = load_active_sets()
    print(f"ingest_date={ingest_date} | aktif set: {len(active)}")

    store = BronzeStore()
    total_pages = total_requests = 0
    last_meta: dict = {}

    with JustTCGExtractor() as ex:
        for source, game, set_id, params in active:
            print(f"[{source}] {game} / {set_id}  params={params}")
            # idempotent: bu setin bugünkü eski sayfalarını temizle
            store.clear_set_date(source=source, game=game, set_id=set_id, ingest_date=ingest_date)
            pages = 0
            for page, resp in ex.iterate_card_pages(game=game, set=set_id, **params):
                key = store.write_page(
                    source=source, game=game, set_id=set_id,
                    page=page, payload=resp, ingest_date=ingest_date,
                )
                n = len(resp.get("data", [])) if isinstance(resp, dict) else 0
                print(f"    page {page}: {n} kart -> {key}")
                pages += 1
                total_requests += 1
                last_meta = resp.get("_metadata", last_meta) if isinstance(resp, dict) else last_meta
            total_pages += pages

    print(f"\nBitti. {len(active)} set, {total_pages} sayfa, {total_requests} istek.")
    if last_meta:
        print(
            f"Kota: günlük kalan {last_meta.get('apiDailyRequestsRemaining')}, "
            f"aylık kalan {last_meta.get('apiRequestsRemaining')}"
        )


if __name__ == "__main__":
    main()
