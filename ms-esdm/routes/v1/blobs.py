import mimetypes
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from services import blob_service
from services.blob_service import sanitize_filename

router = APIRouter()

@router.get("/download/{uuid_filename}")
async def download_blob(uuid_filename: str):
    """
    Download a file by UUID filename.
    """
    file_path = blob_service.BLOB_DIR / uuid_filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        filename=uuid_filename.split("___", 1)[-1]  # serve original filename
    )


@router.get("/preview/{uuid_filename}")
async def preview_blob(uuid_filename: str, request: Request):
    """
    Preview PDF, images, or Word documents in browser (inline).
    """
    try:
        blob = blob_service.get_blob_path_json(uuid_filename, str(request.base_url))
        mime_type, _ = mimetypes.guess_type(blob["file_path"])

        if mime_type is None:
            mime_type = "application/octet-stream"
        safe_filename = sanitize_filename(blob["original_filename"])

        return FileResponse(
            blob["file_path"],
            media_type=mime_type,
            headers={"Content-Disposition": f'inline; filename="{safe_filename}"'}
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
