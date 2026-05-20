"""
Sync Google Drive folder to Knowledge Base server. (need oatuh_client.json as credentials)
Uploads PDF/DOC/DOCX files that don't exist in KB yet.
"""

import os
import tempfile
import requests
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Configuration
KB_BASE_URL = "http://108.136.169.18"
DRIVE_FOLDER_ID = "1MYii1qA_TVhgL77IwEp7OPAnAHmvN9_h"
MAX_UPLOADS = 4  # Set to None for unlimited

ALLOWED_TYPES = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    """Authenticate and return Drive service."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("oauth_client.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open("token.json", "w") as f:
            f.write(creds.to_json())
    
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def fetch_kb_filenames():
    """Get existing filenames from KB (strip prefix before first underscore)."""
    print("[INFO] Fetching KB documents...")
    filenames = set()
    page = 1
    
    while True:
        resp = requests.get(
            f"{KB_BASE_URL}/api/knowledge/documents",
            params={"page": page, "limit": 1000},
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        
        for item in items:
            fn = item.get("filename", "")
            # # Remove prefix before first underscore like "123_originalname.pdf" -> "originalname.pdf"
            # if fn and "_" in fn:
            #     fn = fn.split("_", 1)[1]
            if fn:
                filenames.add(fn)
        
        if len(items) < 1000:
            break
        page += 1
    
    print(f"[INFO] KB unique filenames loaded: {len(filenames)}")
    return filenames


def list_drive_files(service, folder_id):
    """Recursively list all files in Drive folder."""
    print("[INFO] Scanning Drive folder recursively...")
    files = []
    folders = [folder_id]
    visited = set()
    
    while folders:
        current = folders.pop()
        if current in visited:
            continue
        visited.add(current)
        
        page_token = None
        
        while True:
            resp = service.files().list(
                q=f"'{current}' in parents and trashed=false",
                fields="nextPageToken, files(id, name, mimeType, shortcutDetails(targetId, targetMimeType))",
                pageSize=1000,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            for f in resp.get("files", []):
                mime = f.get("mimeType", "")
                
                # Handle regular folders
                if mime == "application/vnd.google-apps.folder":
                    folders.append(f["id"])
                
                # Handle shortcuts
                elif mime == "application/vnd.google-apps.shortcut":
                    shortcut = f.get("shortcutDetails", {})
                    target_id = shortcut.get("targetId")
                    target_mime = shortcut.get("targetMimeType")
                    
                    if target_mime == "application/vnd.google-apps.folder" and target_id:
                        print(f"[INFO] Following shortcut folder: {f['name']}")
                        folders.append(target_id)
                    else:
                        print(f"[SKIP] Shortcut (non-folder): {f['name']}")
                
                # Handle regular files
                else:
                    files.append(f)
            
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
    
    print(f"[INFO] Drive files discovered: {len(files)}")
    return files


def upload_file(service, file_id, filename):
    """Download from Drive and upload to KB."""
    print(f"[DOWNLOAD] {filename}")
    
    # Download to temp file
    temp_fd, temp_path = tempfile.mkstemp(suffix=".tmp")
    os.close(temp_fd)
    
    try:
        request = service.files().get_media(fileId=file_id)
        with open(temp_path, "wb") as f:
            downloader = MediaIoBaseDownload(f, request, chunksize=10*1024*1024)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        
        print(f"[UPLOAD] {filename}")
        
        # Upload to KB
        with open(temp_path, "rb") as f:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            mime_types = {
                "pdf": "application/pdf",
                "doc": "application/msword",
                "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            }
            content_type = mime_types.get(ext, "application/octet-stream")
            
            files = {"file": (filename, f, content_type)}
            resp = requests.post(
                f"{KB_BASE_URL}/api/knowledge/upload",
                files=files,
                timeout=300
            )
            resp.raise_for_status()
        
        print(f"[SUCCESS] {filename}")
        return True
    
    except requests.HTTPError as e:
        response_text = e.response.text if e.response else "No response"
        print(f"[ERROR] {filename} -> HTTP {e.response.status_code if e.response else 'Unknown'}")
        print(f"  Response: {response_text[:500]}")
        return False
    
    except Exception as e:
        print(f"[ERROR] {filename} -> {type(e).__name__}: {e}")
        return False
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def main():
    service = get_drive_service()
    kb_files = fetch_kb_filenames()
    drive_files = list_drive_files(service, DRIVE_FOLDER_ID)
    
    # Filter files to upload
    to_upload = []
    skipped_unsupported = 0
    skipped_exists = 0
    
    for f in drive_files:
        mime = f.get("mimeType", "")
        name = f.get("name", "")
        
        if mime not in ALLOWED_TYPES:
            skipped_unsupported += 1
            continue
        
        if name in kb_files:
            skipped_exists += 1
            continue
        
        to_upload.append(f)
    
    print(f"\n[INFO] Missing in KB (to upload): {len(to_upload)}")
    if skipped_unsupported:
        print(f"[INFO] Unsupported file types skipped (not PDF/DOC/DOCX): {skipped_unsupported}")
    if skipped_exists:
        print(f"[INFO] Files already in KB: {skipped_exists}")
    
    if not to_upload:
        print("[DONE] Nothing to upload.")
        return
    
    if MAX_UPLOADS and len(to_upload) > MAX_UPLOADS:
        remaining = len(to_upload) - MAX_UPLOADS
        to_upload = to_upload[:MAX_UPLOADS]
        print(f"[INFO] Uploading {len(to_upload)} files (limit: {MAX_UPLOADS})")
        print(f"[INFO] {remaining} files will remain for next run")
    else:
        print(f"[INFO] Uploading all {len(to_upload)} files")
    
    # Upload files
    print()
    success = 0
    errors = 0
    
    for i, f in enumerate(to_upload, 1):
        print(f"[{i}/{len(to_upload)}] {f['name']}")
        if upload_file(service, f["id"], f["name"]):
            success += 1
        else:
            errors += 1
    
    print(f"\n[DONE] Sync finished: {success} succeeded, {errors} failed")


if __name__ == "__main__":
    main()