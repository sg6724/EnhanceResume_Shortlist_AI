from __future__ import annotations

BUCKET = "resume-pdfs"


def pdf_path(user_id: str, copy_id: str) -> str:
    return f"{user_id}/{copy_id}.pdf"


async def store_pdf(sb, user_id: str, copy_id: str, pdf_bytes: bytes) -> str:
    """Upload/overwrite the PDF for a resume copy. Returns the storage path
    to persist as resume_copies.pdf_storage_path."""
    path = pdf_path(user_id, copy_id)
    await sb.storage.from_(BUCKET).upload(
        path, pdf_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"},
    )
    return path


async def fetch_pdf(sb, path: str) -> bytes:
    return await sb.storage.from_(BUCKET).download(path)
