from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


@dataclass(slots=True)
class DriveFile:
    id: str
    name: str
    modified_time: str | None


def folder_id_from_url(folder_url: str) -> str:
    parsed = urlparse(folder_url)
    query = parse_qs(parsed.query)
    if "folders" in parsed.path:
        parts = parsed.path.rstrip("/").split("/")
        return parts[-1]
    if "id" in query:
        return query["id"][0]
    raise ValueError(f"No pude extraer el folder id desde: {folder_url}")


def build_drive_service(credentials_json: str | Path):
    creds = Credentials.from_service_account_file(str(credentials_json), scopes=DRIVE_SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def list_pdfs(service, folder_id: str) -> list[DriveFile]:
    query = f"'{folder_id}' in parents and mimeType = 'application/pdf' and trashed = false"
    response = service.files().list(
        q=query,
        orderBy="modifiedTime desc",
        fields="files(id,name,modifiedTime)",
        pageSize=1000,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
    ).execute()
    return [DriveFile(id=item["id"], name=item["name"], modified_time=item.get("modifiedTime")) for item in response.get("files", [])]


def download_pdf(service, file_id: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    destination.write_bytes(buffer.getvalue())
    return destination


def load_credentials_payload(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
