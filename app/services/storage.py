"""
PDF storage — Cloudflare R2 in production, local disk automatically as a
fallback when R2 isn't configured (keeps local dev/testing working with
zero extra setup, exactly as before).

R2 is S3-compatible, so this uses boto3's S3 client pointed at R2's
endpoint. Downloads use short-lived presigned URLs rather than proxying
bytes through our own server — simpler, and R2 serves the bytes directly.
"""
from __future__ import annotations

import os
from pathlib import Path

from app.core.config import get_settings

_LOCAL_DIR = Path(os.getenv("PDF_OUTPUT_DIR", "/tmp/reports"))
_LOCAL_DIR.mkdir(parents=True, exist_ok=True)


def _r2_configured(settings) -> bool:
    return bool(
        settings.r2_account_id
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
        and settings.r2_bucket_name
    )


def _r2_client(settings):
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
    )


def save_pdf(key: str, pdf_bytes: bytes) -> str:
    """
    Store a generated PDF. Returns a storage reference to save on the
    Report row (an R2 object key, or a local file path — the caller
    doesn't need to know which; load_pdf()/get_download_target() handle
    either transparently).
    """
    settings = get_settings()
    if _r2_configured(settings):
        client = _r2_client(settings)
        client.put_object(
            Bucket=settings.r2_bucket_name,
            Key=key,
            Body=pdf_bytes,
            ContentType="application/pdf",
        )
        return f"r2:{key}"
    else:
        path = _LOCAL_DIR / key
        path.write_bytes(pdf_bytes)
        return str(path)


def get_download_target(storage_ref: str, filename: str):
    """
    Given what's stored on Report.storage_url, return how the download
    route should serve it: either ("redirect", presigned_url) for R2, or
    ("file", local_path) for local disk. Keeps portal.py from needing to
    know about R2 vs local at all.
    """
    settings = get_settings()
    if storage_ref.startswith("r2:"):
        key = storage_ref[len("r2:"):]
        client = _r2_client(settings)
        url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.r2_bucket_name,
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=60,  # short-lived; regenerated fresh on every download click
        )
        return ("redirect", url)
    else:
        return ("file", Path(storage_ref))
