"""把乙游素材上传到 MinIO。浏览器通过网站的 /storage/ 读取，不走本机 media 目录。"""
import io
import json
import mimetypes
import os
import uuid

from minio import Minio

_ready_buckets = set()


def _client():
    endpoint = os.environ.get("MINIO_ENDPOINT", "").strip()
    if not endpoint:
        raise RuntimeError("未配置 MINIO_ENDPOINT")
    access_key = os.environ.get("MINIO_ACCESS_KEY", "").strip()
    secret_key = os.environ.get("MINIO_SECRET_KEY", "").strip()
    if not access_key or not secret_key:
        raise RuntimeError("未配置 MINIO 账号")
    secure = os.environ.get("MINIO_SECURE", "0").strip().lower() in {"1", "true", "yes"}
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def _bucket():
    name = os.environ.get("MINIO_BUCKET", "").strip()
    if not name:
        raise RuntimeError("未配置 MINIO_BUCKET")
    return name


def _ensure_bucket(client, bucket):
    if bucket in _ready_buckets:
        return
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


def store_upload(uploaded_file, ext):
    """上传一个文件，返回网站上的访问地址。"""
    suffix = ext if str(ext).startswith(".") else f".{ext}" if ext else ""
    data = uploaded_file.read()
    content_type = (
        getattr(uploaded_file, "content_type", "")
        or mimetypes.guess_type(f"file{suffix}")[0]
        or "application/octet-stream"
    )
    key = f"otome/assets/{uuid.uuid4().hex}{suffix}"
    client = _client()
    bucket = _bucket()
    _ensure_bucket(client, bucket)
    client.put_object(
        bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    base = os.environ.get("OTOME_FRONTEND_BASE", "").strip().rstrip("/")
    if not base:
        raise RuntimeError("未配置 OTOME_FRONTEND_BASE")
    return f"{base}/storage/{key}"
