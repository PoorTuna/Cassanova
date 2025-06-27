import os
from asyncio import gather
from typing import Optional, List
from uuid import uuid4

from fastapi import UploadFile


def get_namespace_dir(namespace: Optional[str] = None, base_dir: str = "/tmp/cassanova-sessions") -> (str, str):
    if namespace is None:
        namespace = str(uuid4())
    path = os.path.join(base_dir, namespace)
    os.makedirs(path, exist_ok=True)
    return path, namespace


async def save_uploaded_files(files: Optional[List[UploadFile]], base_dir: str) -> List[str]:
    if not files:
        return []

    results = await gather(*[_save_file(upload, base_dir) for upload in files])
    saved = [path for path in results if path is not None]
    return saved


async def _save_file(upload: UploadFile, base_dir: str) -> Optional[str]:
    filename = os.path.basename(upload.filename or "").strip()
    if not filename or filename.endswith("/"):
        return None

    dest_path = os.path.join(base_dir, filename)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    content = await upload.read()
    if not content:
        return None

    with open(dest_path, "wb") as f:
        f.write(content)

    return dest_path
