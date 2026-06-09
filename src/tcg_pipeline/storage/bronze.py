"""Bronze katman: ham JSON'u MinIO'ya (S3 uyumlu) yazar.

Key düzeni (Hive-style partition):
  source=<src>/game=<game>/set=<set>/ingest_date=<YYYY-MM-DD>/cards_page=NNNN.json

Tasarım:
- Ham sadakat: API yanıtı (data+meta+_metadata) OLDUĞU GİBİ saklanır.
- Idempotent: aynı (set, gün, sayfa) -> aynı key -> üzerine yazar (F3 retry/backfill).
- Snapshot: ingest_date key'in içinde, her günün kopyası ayrı birikir.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from tcg_pipeline import config

DEFAULT_BUCKET = "bronze"


class BronzeStore:
    def __init__(self, bucket: str | None = None) -> None:
        self.bucket = bucket or config.get("MINIO_BRONZE_BUCKET", DEFAULT_BUCKET)
        self._s3 = boto3.client(
            "s3",
            endpoint_url=config.get("MINIO_ENDPOINT", "http://localhost:9000"),
            aws_access_key_id=config.get("MINIO_ROOT_USER"),
            aws_secret_access_key=config.get("MINIO_ROOT_PASSWORD"),
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",  # MinIO için anlamsız ama boto3 ister
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._s3.head_bucket(Bucket=self.bucket)
        except ClientError:
            self._s3.create_bucket(Bucket=self.bucket)

    @staticmethod
    def _set_date_prefix(source: str, game: str, set_id: str, ingest_date: str) -> str:
        return f"source={source}/game={game}/set={set_id}/ingest_date={ingest_date}/"

    def _key(self, source: str, game: str, set_id: str, ingest_date: str, page: int) -> str:
        return f"{self._set_date_prefix(source, game, set_id, ingest_date)}cards_page={page:04d}.json"

    def clear_set_date(self, *, source: str, game: str, set_id: str, ingest_date: str) -> int:
        """Bir setin o güne ait tüm sayfalarını sil (idempotent yeniden çekim için).

        Sayfa sayısı değişirse (örn. filtre eşiği) eski sayfaların artık kalmasını
        önler. Yazımdan ÖNCE çağrılır.
        """
        prefix = self._set_date_prefix(source, game, set_id, ingest_date)
        resp = self._s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        objs = [{"Key": o["Key"]} for o in resp.get("Contents", [])]
        if objs:
            self._s3.delete_objects(Bucket=self.bucket, Delete={"Objects": objs})
        return len(objs)

    def write_page(
        self,
        *,
        source: str,
        game: str,
        set_id: str,
        page: int,
        payload: dict,
        ingest_date: str | None = None,
    ) -> str:
        """Tek bir ham sayfayı bronze'a yaz, yazılan key'i döndür."""
        ingest_date = ingest_date or datetime.now(UTC).strftime("%Y-%m-%d")
        key = self._key(source, game, set_id, ingest_date, page)
        self._s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )
        return key
