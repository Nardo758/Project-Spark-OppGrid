"""Cloud storage service for dataset file delivery.

Supports Cloudflare R2 (S3-compatible) and AWS S3.
Falls back to local filesystem if no cloud storage is configured.
"""
import os
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CloudStorageService:
    def __init__(self):
        self.provider = os.getenv("FILE_STORAGE_PROVIDER", "local").lower()
        self.bucket = os.getenv("FILE_STORAGE_BUCKET", "")
        self.endpoint = os.getenv("FILE_STORAGE_ENDPOINT", "")
        self.access_key = os.getenv("FILE_STORAGE_ACCESS_KEY", "")
        self.secret_key = os.getenv("FILE_STORAGE_SECRET_KEY", "")
        self.region = os.getenv("FILE_STORAGE_REGION", "auto")
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if self.provider not in ("r2", "s3"):
            return None
        try:
            import boto3
            kwargs = {
                "aws_access_key_id": self.access_key,
                "aws_secret_access_key": self.secret_key,
            }
            if self.endpoint:
                kwargs["endpoint_url"] = self.endpoint
            if self.region:
                kwargs["region_name"] = self.region
            self._client = boto3.client("s3", **kwargs)
            logger.info(f"[CloudStorage] Initialized {self.provider} client")
            return self._client
        except Exception as e:
            logger.error(f"[CloudStorage] Failed to initialize client: {e}")
            return None

    def is_configured(self) -> bool:
        if self.provider == "local":
            return True
        return all([self.bucket, self.access_key, self.secret_key])

    def upload_file(self, local_path: str, object_key: str, content_type: str = "text/csv") -> Tuple[bool, Optional[str]]:
        if self.provider == "local":
            return True, None
        client = self._get_client()
        if not client:
            return False, "Cloud storage client not available"
        try:
            extra_args = {"ContentType": content_type}
            client.upload_file(local_path, self.bucket, object_key, ExtraArgs=extra_args)
            logger.info(f"[CloudStorage] Uploaded {local_path} to {self.bucket}/{object_key}")
            return True, None
        except Exception as e:
            logger.error(f"[CloudStorage] Upload failed: {e}")
            return False, str(e)

    def generate_signed_url(self, object_key: str, expiration_hours: int = 24) -> Tuple[Optional[str], Optional[str]]:
        if self.provider == "local":
            return f"/api/v1/datasets/download/{object_key}", None
        client = self._get_client()
        if not client:
            return None, "Cloud storage client not available"
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_key},
                ExpiresIn=expiration_hours * 3600,
            )
            logger.info(f"[CloudStorage] Generated signed URL for {object_key} (expires in {expiration_hours}h)")
            return url, None
        except Exception as e:
            logger.error(f"[CloudStorage] Failed to generate signed URL: {e}")
            return None, str(e)

    def delete_file(self, object_key: str) -> Tuple[bool, Optional[str]]:
        if self.provider == "local":
            return True, None
        client = self._get_client()
        if not client:
            return False, "Cloud storage client not available"
        try:
            client.delete_object(Bucket=self.bucket, Key=object_key)
            logger.info(f"[CloudStorage] Deleted {self.bucket}/{object_key}")
            return True, None
        except Exception as e:
            logger.error(f"[CloudStorage] Delete failed: {e}")
            return False, str(e)


_cloud_storage = None


def get_cloud_storage() -> CloudStorageService:
    global _cloud_storage
    if _cloud_storage is None:
        _cloud_storage = CloudStorageService()
    return _cloud_storage
