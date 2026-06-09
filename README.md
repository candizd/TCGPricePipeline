# TCG Price Pipeline

Pokémon & One Piece (JP/EN) kart fiyatları için batch ETL pipeline. Çoklu
kaynaktan veri çeker, kuru normalize eder, karşılaştırır; trend + JP/EN primi +
kaynak farkı sinyali üretir. Kaynaklar geçmişi saklamadığı için fiyatları günlük
biriktirir — sistemin temel gerekçesi budur.

> Non-commercial. Scraping yok; sadece ücretsiz API tier'ları (JustTCG,
> PokemonPriceTracker).

## Mimari
API'lar → Airflow → MinIO (bronze) → medallion (bronze→silver→gold) → dbt →
BigQuery sandbox (gold) → Metabase. Local-first, Docker Compose.

## Kurulum
```bash
cp .env.example .env      # anahtarları doldur
uv sync                   # bağımlılıklar
docker compose up -d      # MinIO ayağa kalkar
```
- MinIO console: http://localhost:9001
- MinIO S3 API: http://localhost:9000
