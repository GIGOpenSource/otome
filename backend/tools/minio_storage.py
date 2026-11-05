"""乙游素材上传。STORAGE_BACKEND：1=GCS，2=COS（默认），3=MinIO。返回可公开访问的 URL。"""
import io
import json
import logging
import mimetypes
import os
import uuid

logger = logging.getLogger(__name__)

_ready_buckets = set()
_cos_client = None
_gcs_client = None


def _backend():
    return os.environ.get("STORAGE_BACKEND", "2").strip()


def store_upload(uploaded_file, ext):
    """上传一个文件，返回公开访问地址。"""
    suffix = ext if str(ext).startswith(".") else f".{ext}" if ext else ""
    data = uploaded_file.read()
    content_type = (
        getattr(uploaded_file, "content_type", "")
        or mimetypes.guess_type(f"file{suffix}")[0]
        or "application/octet-stream"
    )
    key = f"otome/assets/{uuid.uuid4().hex}{suffix}"
    backend = _backend()
    if backend == "1":
        return _store_gcs(data, key, content_type)
    if backend == "3":
        return _store_minio(data, key, content_type)
    return _store_cos(data, key, content_type)


def _store_cos(data, key, content_type):
    client = _get_cos_client()
    if client is None:
        raise RuntimeError("未配置 COS（COS_SECRET_ID / COS_SECRET_KEY / COS_BUCKET / COS_REGION）")
    bucket = os.environ.get("COS_BUCKET", "").strip()
    if not bucket:
        raise RuntimeError("未配置 COS_BUCKET")
    client.put_object(
        Bucket=bucket,
        Body=data,
        Key=key,
        ContentType=content_type,
        EnableMD5=False,
    )
    return _cos_public_url(key)


def _get_cos_client():
    global _cos_client
    if _cos_client is not None:
        return _cos_client
    secret_id = (
        os.environ.get("COS_SECRET_ID", "").strip()
        or os.environ.get("TENCENT_COS_SECRET_ID", "").strip()
    )
    secret_key = (
        os.environ.get("COS_SECRET_KEY", "").strip()
        or os.environ.get("TENCENT_COS_SECRET_KEY", "").strip()
    )
    region = (
        os.environ.get("COS_REGION", "").strip()
        or os.environ.get("TENCENT_COS_REGION", "").strip()
    )
    if not secret_id or not secret_key or not region:
        return None
    from qcloud_cos import CosConfig, CosS3Client

    _cos_client = CosS3Client(CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key))
    logger.info("COS 客户端初始化成功 (region=%s)", region)
    return _cos_client


def _cos_public_url(key):
    domain = os.environ.get("COS_DOMAIN", "").strip().rstrip("/")
    if domain:
        if domain.startswith("http://") or domain.startswith("https://"):
            return f"{domain}/{key}"
        return f"https://{domain}/{key}"
    bucket = (
        os.environ.get("COS_BUCKET", "").strip()
        or os.environ.get("TENCENT_COS_BUCKET", "").strip()
    )
    region = (
        os.environ.get("COS_REGION", "").strip()
        or os.environ.get("TENCENT_COS_REGION", "").strip()
        or "ap-beijing"
    )
    return f"https://{bucket}.cos.{region}.myqcloud.com/{key}"


def _store_gcs(data, key, content_type):
    bucket = _get_gcs_bucket()
    if bucket is None:
        raise RuntimeError("未配置 GCS（GCS_BUCKET / GCS_CREDENTIALS）")
    blob = bucket.blob(key)
    blob.upload_from_string(data, content_type=content_type)
    return _gcs_public_url(key)


def _get_gcs_client():
    global _gcs_client
    if _gcs_client is not None:
        return _gcs_client
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise RuntimeError("未安装 google-cloud-storage，请重建 otome-base 镜像") from exc

    creds = (
        os.environ.get("GCS_CREDENTIALS", "").strip()
        or os.environ.get("GCS_CREDENTIALS_PROD", "").strip()
        or os.environ.get("GCS_CREDENTIALS_LOCAL", "").strip()
    )
    if creds and os.path.isfile(creds):
        _gcs_client = storage.Client.from_service_account_json(creds)
    else:
        _gcs_client = storage.Client()
    logger.info("GCS 客户端初始化成功 (bucket=%s)", os.environ.get("GCS_BUCKET", ""))
    return _gcs_client


def _get_gcs_bucket():
    name = os.environ.get("GCS_BUCKET", "").strip()
    if not name:
        return None
    client = _get_gcs_client()
    return client.bucket(name)


def _gcs_public_url(key):
    custom = os.environ.get("GCS_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if custom:
        return f"{custom}/{key}"
    bucket = os.environ.get("GCS_BUCKET", "").strip()
    return f"https://storage.googleapis.com/{bucket}/{key}"


def _store_minio(data, key, content_type):
    from minio import Minio

    endpoint = os.environ.get("MINIO_ENDPOINT", "").strip()
    if not endpoint:
        raise RuntimeError("未配置 MINIO_ENDPOINT")
    access_key = os.environ.get("MINIO_ACCESS_KEY", "").strip()
    secret_key = os.environ.get("MINIO_SECRET_KEY", "").strip()
    if not access_key or not secret_key:
        raise RuntimeError("未配置 MINIO 账号")
    bucket = os.environ.get("MINIO_BUCKET", "").strip()
    if not bucket:
        raise RuntimeError("未配置 MINIO_BUCKET")
    secure = os.environ.get("MINIO_SECURE", "0").strip().lower() in {"1", "true", "yes"}
    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
    if bucket not in _ready_buckets:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        client.set_bucket_policy(bucket, json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket}/*"],
            }],
        }))
        _ready_buckets.add(bucket)
    client.put_object(
        bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    public = os.environ.get("MINIO_PUBLIC_BASE", "").strip().rstrip("/")
    if public:
        return f"{public}/{bucket}/{key}"
    scheme = "https" if secure else "http"
    return f"{scheme}://{endpoint}/{bucket}/{key}"
