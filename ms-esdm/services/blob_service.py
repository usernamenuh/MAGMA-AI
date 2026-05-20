import re
import unicodedata
from pathlib import Path

BLOB_DIR = Path("blobs")
BLOB_DIR.mkdir(parents=True, exist_ok=True)

def get_blob_path_json(uuid_filename: str, base_url: str) -> dict:
    # Search for any file containing the uuid_filename
    matches = [f for f in BLOB_DIR.iterdir() if uuid_filename in f.name]

    print("Searching for:", uuid_filename)
    print("Files in dir:", [f.name for f in BLOB_DIR.iterdir()])

    if not matches:
        raise FileNotFoundError(f"No file containing '{uuid_filename}' found")

    # Use the first match
    file_path = matches[0]
    full_filename = file_path.name

    # Extract original name: {uuid}___{original}
    parts = full_filename.split("___", 1)
    original_filename = parts[1] if len(parts) > 1 else full_filename

    return {
        "uuid_filename": full_filename,
        "original_filename": original_filename,
        "url": f"{base_url}blobs/download/{full_filename}",
        "path": str(file_path),
        "file_path": file_path,
    }


def sanitize_filename(name: str) -> str:
    # Normalize accents
    name = unicodedata.normalize("NFKD", name)
    # Keep ASCII only
    name = name.encode("ascii", "ignore").decode("ascii")
    # Replace spaces with underscores (optional)
    return re.sub(r"\s+", "_", name)