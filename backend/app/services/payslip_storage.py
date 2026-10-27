"""Private, on-disk storage for uploaded payslip PDFs.

File names are always derived from server-generated UUIDs (user_id,
payslip_id), never from the client-supplied filename, so there is no path
traversal surface. The storage root lives outside any directory served
statically by the API - nothing under it is publicly accessible.
"""

from pathlib import Path
from uuid import UUID

from app.config import settings

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def storage_root() -> Path:
    root = Path(settings.upload_dir)
    if not root.is_absolute():
        root = _BACKEND_ROOT / root
    return root


def save_payslip_file(user_id: UUID, payslip_id: UUID, data: bytes) -> str:
    user_dir = storage_root() / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    destination = user_dir / f"{payslip_id}.pdf"
    destination.write_bytes(data)
    return str(destination)


def delete_payslip_file(file_path: str | None) -> None:
    if not file_path:
        return
    path = Path(file_path)
    if path.exists():
        path.unlink(missing_ok=True)
