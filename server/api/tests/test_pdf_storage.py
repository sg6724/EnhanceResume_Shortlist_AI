from __future__ import annotations

import pytest

from app.services import pdf_storage


class _FakeBucketProxy:
    def __init__(self, download_bytes=None, upload_exc=None, download_exc=None):
        self.uploaded: list[tuple[str, bytes, dict]] = []
        self._download_bytes = download_bytes
        self._upload_exc = upload_exc
        self._download_exc = download_exc

    async def upload(self, path, file, file_options=None):
        if self._upload_exc:
            raise self._upload_exc
        self.uploaded.append((path, file, file_options))
        return {"path": path}

    async def download(self, path):
        if self._download_exc:
            raise self._download_exc
        return self._download_bytes


class _FakeStorage:
    def __init__(self, bucket_proxy):
        self._bucket_proxy = bucket_proxy
        self.requested_bucket = None

    def from_(self, bucket_id):
        self.requested_bucket = bucket_id
        return self._bucket_proxy


class _FakeSupabase:
    def __init__(self, bucket_proxy):
        self.storage = _FakeStorage(bucket_proxy)


def test_pdf_path_format():
    assert pdf_storage.pdf_path("user-1", "copy-1") == "user-1/copy-1.pdf"


async def test_store_pdf_uploads_with_correct_bucket_and_options():
    bucket = _FakeBucketProxy()
    sb = _FakeSupabase(bucket)

    path = await pdf_storage.store_pdf(sb, "user-1", "copy-1", b"%PDF-1.4 fake bytes")

    assert path == "user-1/copy-1.pdf"
    assert sb.storage.requested_bucket == pdf_storage.BUCKET
    assert bucket.uploaded == [
        ("user-1/copy-1.pdf", b"%PDF-1.4 fake bytes", {"content-type": "application/pdf", "upsert": "true"})
    ]


async def test_fetch_pdf_downloads_from_correct_bucket():
    bucket = _FakeBucketProxy(download_bytes=b"the pdf bytes")
    sb = _FakeSupabase(bucket)

    result = await pdf_storage.fetch_pdf(sb, "user-1/copy-1.pdf")

    assert result == b"the pdf bytes"
    assert sb.storage.requested_bucket == pdf_storage.BUCKET


async def test_store_pdf_propagates_upload_errors():
    bucket = _FakeBucketProxy(upload_exc=RuntimeError("storage down"))
    sb = _FakeSupabase(bucket)

    with pytest.raises(RuntimeError):
        await pdf_storage.store_pdf(sb, "user-1", "copy-1", b"bytes")
