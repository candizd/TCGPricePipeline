"""F1 keşif: JustTCG'de oyun/set yapısını ve JP/EN ayrımını ortaya çıkar.

Az istek harcar (~4): /games, /sets (pokemon + one-piece), örnek /cards.
Ham yanıtları data/exploration/ altına yazar (inceleme + şema doğrulama için).

Çalıştır:  uv run python scripts/explore_justtcg.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tcg_pipeline.extractors.justtcg import JustTCGExtractor

# Windows konsolu cp1252 — Türkçe karakter için UTF-8'e zorla
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OUT = Path("data/exploration")
OUT.mkdir(parents=True, exist_ok=True)


def dump(name: str, obj: object) -> None:
    (OUT / f"{name}.json").write_text(json.dumps(obj, indent=2, ensure_ascii=False), "utf-8")
    print(f"  -> data/exploration/{name}.json")


def main() -> None:
    with JustTCGExtractor() as ex:
        print("[1] /games")
        games = ex.list_games()
        dump("games", games)
        glist = games.get("data", games) if isinstance(games, dict) else games
        ids = [g.get("id") or g.get("game") for g in glist] if isinstance(glist, list) else []
        print(f"      oyunlar: {ids}")
        # JP/EN ipucu: game id'lerinde japan/jp geçen var mı?
        jp_games = [i for i in ids if i and any(k in str(i).lower() for k in ("japan", "jp"))]
        print(f"      JP-benzeri game id'leri: {jp_games or 'YOK (dil set seviyesinde olabilir)'}")

        for game in ("pokemon", "pokemon-japan", "one-piece-card-game"):
            print(f"[*] /sets?game={game}")
            try:
                sets = ex.list_sets(game)
            except Exception as e:  # noqa: BLE001 — keşifte hatayı görmek istiyoruz
                print(f"      HATA: {e}")
                continue
            dump(f"sets_{game}", sets)
            slist = sets.get("data", sets) if isinstance(sets, dict) else sets
            names = [s.get("name", "") for s in slist] if isinstance(slist, list) else []
            jp_sets = [n for n in names if any(k in n.lower() for k in ("japan", "japanese", "jp"))]
            print(f"      toplam set: {len(names)} | JP-benzeri set: {len(jp_sets)}")
            print(f"      ilk 5 set: {names[:5]}")
            print(f"      JP-benzeri ilk 5: {jp_sets[:5] or 'YOK'}")

        print("[*] örnek /cards (şema doğrulama): game=pokemon&limit=2")
        sample = ex.get_cards(game="pokemon", limit=2)
        dump("sample_cards", sample)
        print("      -> variant alanlarını sample_cards.json'da kontrol et (language var mı?)")

    print("\nKeşif bitti. data/exploration/ içindeki JSON'ları incele.")


if __name__ == "__main__":
    main()
