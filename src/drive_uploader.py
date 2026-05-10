import base64
import json
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from src.config import GOOGLE_SERVICE_ACCOUNT_B64, GOOGLE_DRIVE_FOLDER_ID

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def _get_drive_service():
    if not GOOGLE_SERVICE_ACCOUNT_B64:
        raise EnvironmentError("GOOGLE_SERVICE_ACCOUNT_B64 not set")
    sa_json = base64.b64decode(GOOGLE_SERVICE_ACCOUNT_B64).decode()
    sa_info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def upload_pdf(pdf_path: str, filename: str) -> str:
    """Upload PDF to Google Drive folder, return shareable link."""
    service = _get_drive_service()
    file_metadata = {
        "name": filename,
        "parents": [GOOGLE_DRIVE_FOLDER_ID],
    }
    media = MediaFileUpload(pdf_path, mimetype="application/pdf")
    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()
    file_id = uploaded.get("id")
    # Make publicly readable
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"}
    ).execute()
    return f"https://drive.google.com/file/d/{file_id}/view"
